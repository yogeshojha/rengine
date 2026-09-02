<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Rocket from '@lucide/svelte/icons/rocket';

	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Badge } from '$lib/components/ui/badge';
	import { Label } from '$lib/components/ui/label';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import ExecutionPreview from './execution-preview.svelte';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import ContextSections from '$lib/components/contexts/context-sections.svelte';
	import {
		validateDraft,
		buildContextPayload,
		type ContextFormSection
	} from '$lib/components/contexts/context-form';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansApi } from '$lib/api/scans';
	import { targetsApi } from '$lib/api/targets';
	import { DEFAULT_SCAN_CONTEXT, type ScanContextCreate } from '$lib/types/scan-context';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { MAX_SCAN_BATCH } from '$lib/types/scan';
	import type { Target } from '$lib/types/target';
	import type { ScanPreview } from '$lib/types/scan';

	interface Props {
		open: boolean;
		targetId?: string;
		targetIds?: string[];
		presetEngineId?: string;
		presetContextId?: string;
		onClose?: () => void;
	}

	let {
		open = $bindable(),
		targetId,
		targetIds,
		presetEngineId,
		presetContextId,
		onClose
	}: Props = $props();

	const CTX_MODAL_SECTIONS: ContextFormSection[] = ['scope', 'auth', 'rate', 'runtime', 'proxy'];
	const TARGET_PAGE_SIZE = 100;
	const TARGET_FETCH_CONCURRENCY = 10;

	let view = $state<'launch' | 'newContext'>('launch');

	let engineId = $state<string>('');
	let contextId = $state<string>(SELECT_NONE);
	let selectedTargetIds = $state<string[]>([]);

	let targets = $state<Target[]>([]);
	let targetsLoading = $state(false);
	let targetsError = $state<string | null>(null);
	let unresolvedTargets = $state(0);
	let preview = $state<ScanPreview | null>(null);
	let previewLoading = $state(false);
	let previewError = $state<string | null>(null);
	let launching = $state(false);

	let engineTrigger = $state<HTMLButtonElement | null>(null);

	let previewDebounce: ReturnType<typeof setTimeout>;
	let previewSeq = 0;

	let lockedTarget = $derived(targetId ? (targets.find((t) => t.id === targetId) ?? null) : null);
	let lockedTargetValue = $derived(lockedTarget?.target_value ?? '');
	let selectedTargets = $derived(
		selectedTargetIds.map((id) => targets.find((t) => t.id === id)).filter((t): t is Target => !!t)
	);
	let currentTargetValue = $derived(lockedTargetValue || (selectedTargets[0]?.target_value ?? ''));
	let previewTargetId = $derived(selectedTargetIds[0] ?? '');
	let targetItems = $derived(targets.map((t) => ({ id: t.id, label: t.target_value })));
	let selectedTargetItems = $derived(
		selectedTargetIds.map((id) => ({
			id,
			label: targets.find((t) => t.id === id)?.target_value ?? id
		}))
	);

	let enginesReady = $derived(
		(scanEnginesStore.hasFetched || !!scanEnginesStore.error) && !scanEnginesStore.isLoading
	);
	let contextsReady = $derived(
		(scanContextsStore.hasFetched || !!scanContextsStore.error) && !scanContextsStore.isLoading
	);
	let noEngines = $derived(
		enginesReady && !scanEnginesStore.error && scanEnginesStore.engines.length === 0
	);
	let noTargets = $derived(!targetsLoading && !targetsError && targets.length === 0);

	let engineLabel = $derived(
		scanEnginesStore.engines.find((e) => e.id === engineId)?.name ?? 'Select engine'
	);
	let contextLabel = $derived(
		contextId === SELECT_NONE
			? 'None — engine defaults'
			: (scanContextsStore.contexts.find((c) => c.id === contextId)?.name ?? 'Select context')
	);

	let overBatchLimit = $derived(selectedTargetIds.length > MAX_SCAN_BATCH);

	let launchBlockReason = $derived.by(() => {
		if (noEngines) return 'Create a scan engine first.';
		if (!engineId) return 'Select an engine to launch.';
		if (selectedTargetIds.length === 0) return 'Select at least one target to launch.';
		if (overBatchLimit) return `Select at most ${MAX_SCAN_BATCH} targets.`;
		return null;
	});

	let canLaunch = $derived(
		!!engineId && selectedTargetIds.length > 0 && !overBatchLimit && !launching
	);

	let savingContext = $state(false);
	let ctxDraft = $state<ScanContextCreate | null>(null);
	let ctxTouched = new SvelteSet<string>();
	let ctxNameEl = $state<HTMLInputElement | null>(null);
	let ctxOpen = $state<Record<ContextFormSection, boolean>>({
		identity: false,
		auth: false,
		rate: false,
		scope: true,
		runtime: false,
		proxy: false
	});
	let ctxValidation = $derived(ctxDraft ? validateDraft(ctxDraft) : null);

	$effect(() => {
		if (!open) return;
		const project = projectsStore.activeProject;
		if (!project) return;
		untrack(() => {
			if (scanEnginesStore.fetchedProjectId !== project.id)
				scanEnginesStore.fetchEngines(project.id);
			if (scanContextsStore.fetchedProjectId !== project.id)
				scanContextsStore.fetchContexts(project.id);
			selectedTargetIds = targetId ? [targetId] : [...(targetIds ?? [])];
			loadTargets(project.slug, selectedTargetIds);
		});
	});

	let prefsRestored = $state(false);
	$effect(() => {
		if (!open) {
			prefsRestored = false;
			return;
		}
		if (enginesReady && contextsReady && !prefsRestored) {
			prefsRestored = true;
			untrack(() => {
				restorePreferences();
				if (presetEngineId) engineId = presetEngineId;
				if (presetContextId) contextId = presetContextId;
				focusEngine();
			});
		}
	});

	function restorePreferences() {
		if (typeof localStorage === 'undefined') return;
		if (!engineId) {
			const lastEngine = localStorage.getItem(STORAGE_KEYS.launchLastEngine);
			if (lastEngine && scanEnginesStore.engines.some((e) => e.id === lastEngine)) {
				engineId = lastEngine;
			}
		}
		const lastContext = localStorage.getItem(STORAGE_KEYS.launchLastContext);
		if (lastContext === SELECT_NONE) {
			contextId = SELECT_NONE;
		} else if (lastContext && scanContextsStore.contexts.some((c) => c.id === lastContext)) {
			contextId = lastContext;
		}
	}

	async function focusEngine() {
		await tick();
		engineTrigger?.focus();
	}

	async function loadTargets(projectSlug: string, ensureIds: string[] = []) {
		targetsLoading = true;
		targetsError = null;
		unresolvedTargets = 0;
		try {
			const res = await targetsApi.list({ project_slug: projectSlug, size: TARGET_PAGE_SIZE });
			const loaded = res.items;
			const known = new SvelteSet(loaded.map((t) => t.id));
			const missing = ensureIds.filter((id) => !known.has(id)).slice(0, MAX_SCAN_BATCH);
			for (let i = 0; i < missing.length; i += TARGET_FETCH_CONCURRENCY) {
				const fetched = await Promise.all(
					missing
						.slice(i, i + TARGET_FETCH_CONCURRENCY)
						.map((id) => targetsApi.get(id).catch(() => null))
				);
				for (const t of fetched) {
					if (!t) continue;
					loaded.push(t);
					known.add(t.id);
				}
			}
			targets = loaded;
			const kept = selectedTargetIds.filter((id) => known.has(id));
			unresolvedTargets = selectedTargetIds.length - kept.length;
			selectedTargetIds = kept;
		} catch (e) {
			targetsError = e instanceof Error ? e.message : 'Failed to load targets';
			selectedTargetIds = [];
		} finally {
			targetsLoading = false;
		}
	}

	function retryEngines() {
		const project = projectsStore.activeProject;
		if (project) scanEnginesStore.fetchEngines(project.id);
	}

	function retryContexts() {
		const project = projectsStore.activeProject;
		if (project) scanContextsStore.fetchContexts(project.id);
	}

	function retryTargets() {
		const project = projectsStore.activeProject;
		if (project) loadTargets(project.slug, selectedTargetIds);
	}

	function runPreview() {
		const eng = engineId;
		const ctx = contextId;
		const tgt = previewTargetId;
		const project = projectsStore.activeProject;

		clearTimeout(previewDebounce);
		if (!eng || !tgt || !project) {
			preview = null;
			previewLoading = false;
			previewError = null;
			return;
		}

		previewLoading = true;
		previewError = null;
		const seq = ++previewSeq;
		previewDebounce = setTimeout(async () => {
			try {
				const result = await scansApi.preview(project.id, {
					engine_id: eng,
					context_id: ctx === SELECT_NONE ? null : ctx,
					target_id: tgt
				});
				if (seq === previewSeq) {
					preview = result;
					previewError = null;
				}
			} catch (e) {
				if (seq === previewSeq) {
					previewError = e instanceof Error ? e.message : 'Failed to preview scan';
				}
			} finally {
				if (seq === previewSeq) previewLoading = false;
			}
		}, 350);
	}

	$effect(() => {
		void engineId;
		void contextId;
		void previewTargetId;
		void projectsStore.activeProject?.id;
		runPreview();
	});

	function rememberPreferences() {
		if (typeof localStorage === 'undefined') return;
		if (engineId) localStorage.setItem(STORAGE_KEYS.launchLastEngine, engineId);
		localStorage.setItem(STORAGE_KEYS.launchLastContext, contextId);
	}

	async function handleLaunch() {
		const project = projectsStore.activeProject;
		if (!project || !canLaunch) return;
		launching = true;
		try {
			const created = await scansStore.launchScans(project.id, {
				engine_id: engineId,
				context_id: contextId === SELECT_NONE ? null : contextId,
				target_ids: selectedTargetIds
			});
			if (created) {
				rememberPreferences();
				const label = created.length === 1 ? 'Scan queued' : `${created.length} scans queued`;
				toast.success(`${label} — execution starts when a scanner is connected.`);
				handleOpenChange(false);
				goto(ROUTES.scans);
			} else {
				toast.error(scansStore.error ?? 'Failed to launch scan');
			}
		} finally {
			launching = false;
		}
	}

	function gotoCreateEngine() {
		handleOpenChange(false);
		goto(ROUTES.engines);
	}

	async function startNewContext() {
		const d = DEFAULT_SCAN_CONTEXT();
		d.name = currentTargetValue ? `${currentTargetValue} — scope` : '';
		ctxDraft = d;
		ctxTouched.clear();
		ctxOpen = {
			identity: false,
			auth: false,
			rate: false,
			scope: true,
			runtime: false,
			proxy: false
		};
		view = 'newContext';
		await tick();
		ctxNameEl?.focus();
		ctxNameEl?.select();
	}

	function patchCtx(updates: Partial<ScanContextCreate>) {
		if (!ctxDraft) return;
		ctxDraft = { ...ctxDraft, ...updates };
	}

	function cancelNewContext() {
		view = 'launch';
		ctxDraft = null;
	}

	async function createAndUseContext() {
		const project = projectsStore.activeProject;
		if (!project || !ctxDraft || savingContext) return;
		const issue = validateDraft(ctxDraft);
		if (issue) {
			if (issue.section === 'identity') ctxNameEl?.focus();
			else ctxOpen[issue.section] = true;
			toast.error(issue.message);
			return;
		}
		savingContext = true;
		try {
			const created = await scanContextsStore.createContext(
				project.id,
				buildContextPayload(ctxDraft, ctxTouched)
			);
			if (created) {
				contextId = created.id;
				toast.success(`Context "${created.name}" created — applied to this scan.`);
				view = 'launch';
				ctxDraft = null;
			} else {
				toast.error(scanContextsStore.error ?? 'Failed to create context');
			}
		} finally {
			savingContext = false;
		}
	}

	function reset() {
		engineId = '';
		contextId = SELECT_NONE;
		selectedTargetIds = [];
		preview = null;
		previewLoading = false;
		previewError = null;
		targetsError = null;
		unresolvedTargets = 0;
		view = 'launch';
		ctxDraft = null;
		clearTimeout(previewDebounce);
	}

	function handleOpenChange(isOpen: boolean) {
		open = isOpen;
		if (!isOpen) {
			reset();
			onClose?.();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (view !== 'launch') return;
		if (e.key === 'Enter' && canLaunch && !(e.target instanceof HTMLTextAreaElement)) {
			e.preventDefault();
			handleLaunch();
		}
	}
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content
		class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-[760px]"
		onkeydown={handleKeydown}
	>
		{#if view === 'launch'}
			<Dialog.Header class="p-6 pb-4">
				<Dialog.Title>New Scan</Dialog.Title>
				<Dialog.Description>
					Combine a scan engine with an optional context, preview the resolved plan, then queue it.
				</Dialog.Description>
			</Dialog.Header>

			<Separator />

			<div class="grid h-[60vh] min-h-0 grid-cols-1 gap-0 overflow-hidden md:grid-cols-2">
				<!-- Selections -->
				<ScrollArea class="h-full min-h-0">
					<div class="space-y-4 p-6">
						<!-- Engine -->
						<div class="space-y-2">
							<Label for="scan-engine-select">Engine <span class="text-destructive">*</span></Label>
							{#if !enginesReady}
								<Skeleton class="h-9 w-full rounded-md" />
							{:else if scanEnginesStore.error}
								<div
									class="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive"
								>
									<AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
									<div class="space-y-1">
										<p>{scanEnginesStore.error}</p>
										<Button
											variant="outline"
											size="sm"
											class="h-7 gap-1 text-xs"
											onclick={retryEngines}
										>
											<RefreshCw class="h-3 w-3" /> Retry
										</Button>
									</div>
								</div>
							{:else if noEngines}
								<div
									class="space-y-2 rounded-md border border-border bg-muted/20 px-3 py-3 text-xs"
								>
									<p class="text-muted-foreground">
										No scan engines yet. Create one to define what a scan runs.
									</p>
									<Button
										variant="outline"
										size="sm"
										class="h-7 gap-1 text-xs"
										onclick={gotoCreateEngine}
									>
										<Plus class="h-3 w-3" /> Create a scan engine
									</Button>
								</div>
							{:else}
								<Select.Root type="single" bind:value={engineId}>
									<Select.Trigger id="scan-engine-select" class="w-full" bind:ref={engineTrigger}>
										{engineLabel}
									</Select.Trigger>
									<Select.Content>
										{#each scanEnginesStore.engines as engine (engine.id)}
											<Select.Item value={engine.id} label={engine.name}>{engine.name}</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							{/if}
						</div>

						<!-- Context -->
						<div class="space-y-2">
							<div class="flex items-center justify-between">
								<Label for="scan-context-select">Context</Label>
								{#if contextsReady && !scanContextsStore.error}
									<Button
										variant="ghost"
										size="sm"
										class="h-6 gap-1 px-2 text-xs text-muted-foreground"
										onclick={startNewContext}
									>
										<Plus class="h-3 w-3" /> New context
									</Button>
								{/if}
							</div>
							{#if !contextsReady}
								<Skeleton class="h-9 w-full rounded-md" />
							{:else if scanContextsStore.error}
								<div
									class="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive"
								>
									<AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
									<div class="space-y-1">
										<p>{scanContextsStore.error}</p>
										<Button
											variant="outline"
											size="sm"
											class="h-7 gap-1 text-xs"
											onclick={retryContexts}
										>
											<RefreshCw class="h-3 w-3" /> Retry
										</Button>
									</div>
								</div>
							{:else}
								<Select.Root type="single" bind:value={contextId}>
									<Select.Trigger id="scan-context-select" class="w-full"
										>{contextLabel}</Select.Trigger
									>
									<Select.Content>
										<Select.Item value={SELECT_NONE} label="None — engine defaults">
											None — engine defaults
										</Select.Item>
										{#each scanContextsStore.contexts as context (context.id)}
											<Select.Item value={context.id} label={context.name}
												>{context.name}</Select.Item
											>
										{/each}
									</Select.Content>
								</Select.Root>
							{/if}
						</div>

						<!-- Target -->
						<div class="space-y-2">
							<Label for="scan-target-select">Target <span class="text-destructive">*</span></Label>
							{#if targetId}
								{#if lockedTarget}
									<div
										id="scan-target-select"
										class="flex h-9 w-full items-center gap-2 rounded-md border border-border bg-muted/30 px-3 text-sm"
									>
										<Badge variant="secondary" class="font-mono font-normal"
											>{lockedTarget.target_value}</Badge
										>
										<span class="text-xs text-muted-foreground">{lockedTarget.target_type}</span>
									</div>
								{:else}
									<Skeleton class="h-9 w-full rounded-md" />
								{/if}
							{:else if targetsLoading}
								<Skeleton class="h-9 w-full rounded-md" />
							{:else if targetsError}
								<div
									class="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive"
								>
									<AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
									<div class="space-y-1">
										<p>{targetsError}</p>
										<Button
											variant="outline"
											size="sm"
											class="h-7 gap-1 text-xs"
											onclick={retryTargets}
										>
											<RefreshCw class="h-3 w-3" /> Retry
										</Button>
									</div>
								</div>
							{:else if noTargets}
								<div
									class="space-y-2 rounded-md border border-border bg-muted/20 px-3 py-3 text-xs"
								>
									<p class="text-muted-foreground">No targets yet. Add one to scan.</p>
									<Button
										variant="outline"
										size="sm"
										class="h-7 gap-1 text-xs"
										onclick={() => {
											handleOpenChange(false);
											goto(ROUTES.targets);
										}}
									>
										<Plus class="h-3 w-3" /> Go to targets
									</Button>
								</div>
							{:else}
								<MultiSelectCombobox
									id="scan-target-select"
									items={targetItems}
									selected={selectedTargetItems}
									onSelect={(item) =>
										(selectedTargetIds = selectedTargetIds.includes(item.id)
											? selectedTargetIds
											: [...selectedTargetIds, item.id])}
									onRemove={(item) =>
										(selectedTargetIds = selectedTargetIds.filter((id) => id !== item.id))}
									allowCreate={false}
									placeholder="Search targets…"
									emptyText="No targets in this project."
								/>
								{#if unresolvedTargets > 0}
									<p class="text-[11px] text-warning">
										{unresolvedTargets}
										{unresolvedTargets === 1 ? 'target' : 'targets'} could not be loaded and {unresolvedTargets ===
										1
											? 'was'
											: 'were'} removed from this scan.
									</p>
								{/if}
								{#if selectedTargetIds.length > 1}
									<p class="text-[11px] text-muted-foreground">Each target runs as its own scan.</p>
								{/if}
							{/if}
						</div>
					</div>
				</ScrollArea>

				<!-- Preview -->
				<ScrollArea class="h-full min-h-0 border-t bg-muted/20 md:border-t-0 md:border-l">
					<div class="p-6">
						{#if selectedTargetIds.length > 1 && !previewError && (preview || previewLoading)}
							<p
								class="mb-4 rounded-md border border-border bg-background px-3 py-2 text-xs text-muted-foreground"
							>
								Preview is for <span class="font-mono text-foreground">{currentTargetValue}</span>.
								All {selectedTargetIds.length} targets queue with this engine and context.
							</p>
						{/if}
						{#if previewError}
							<div
								class="flex h-full min-h-[200px] flex-col items-center justify-center gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-8 text-center"
							>
								<AlertTriangle class="h-8 w-8 text-destructive" />
								<div class="space-y-1">
									<p class="text-sm font-medium text-foreground">Couldn't build the preview</p>
									<p class="text-xs text-muted-foreground">{previewError}</p>
								</div>
								<Button variant="outline" size="sm" class="gap-1" onclick={runPreview}>
									<RefreshCw class="h-3.5 w-3.5" /> Retry
								</Button>
							</div>
						{:else if previewLoading && preview}
							<div class="relative">
								<div class="pointer-events-none opacity-40 transition-opacity">
									<ExecutionPreview {preview} loading={false} />
								</div>
								<div
									class="absolute inset-x-0 top-0 flex items-center justify-center gap-2 text-xs text-muted-foreground"
								>
									<Spinner class="h-3.5 w-3.5" />
									Updating preview…
								</div>
							</div>
						{:else}
							<ExecutionPreview {preview} loading={previewLoading} />
						{/if}
					</div>
				</ScrollArea>
			</div>

			<Separator />

			<div class="flex flex-col gap-3 bg-muted/30 p-4">
				<p class="text-xs text-muted-foreground">
					Launching records the resolved config and queues it — execution runs once a scanner is
					connected.
				</p>
				<div class="flex items-center justify-end gap-3">
					{#if launchBlockReason}
						<span class="text-xs text-muted-foreground">{launchBlockReason}</span>
					{/if}
					<Button variant="outline" onclick={() => handleOpenChange(false)} disabled={launching}>
						Cancel
					</Button>
					<Button onclick={handleLaunch} disabled={!canLaunch} class="gap-2">
						{#if launching}
							<Spinner class="h-4 w-4" />
							Queuing…
						{:else}
							<Rocket class="h-4 w-4" />
							{#if lockedTargetValue}
								Queue scan against {lockedTargetValue}
							{:else if selectedTargetIds.length > 1}
								Queue {selectedTargetIds.length} scans
							{:else}
								Queue scan
							{/if}
						{/if}
					</Button>
				</div>
			</div>
		{:else}
			<Dialog.Header class="p-6 pb-4">
				<Button
					variant="ghost"
					size="sm"
					class="-ml-2 h-7 w-fit gap-1 px-2 text-xs text-muted-foreground"
					onclick={cancelNewContext}
				>
					<ChevronLeft class="h-3.5 w-3.5" /> Back
				</Button>
				<Dialog.Title>New context</Dialog.Title>
				<Dialog.Description>
					Tune scope, auth and rate{currentTargetValue ? ` for ${currentTargetValue}` : ''}. Saved
					as a reusable context you can pick again.
				</Dialog.Description>
			</Dialog.Header>

			<Separator />

			<ScrollArea class="h-[60vh]">
				<div class="space-y-4 p-6">
					<div class="space-y-1.5">
						<Label for="ctx-name">Name <span class="text-destructive">*</span></Label>
						<Input
							id="ctx-name"
							bind:ref={ctxNameEl}
							value={ctxDraft?.name ?? ''}
							oninput={(e) => patchCtx({ name: e.currentTarget.value })}
							placeholder="e.g. google.com — staging excluded"
							class="h-9"
						/>
						<p class="text-[11px] text-muted-foreground">
							Scope is open below — add out-of-scope subdomains, paths or IPs to keep them out of
							this scan.
						</p>
					</div>
					{#if ctxDraft}
						<ContextSections
							draft={ctxDraft}
							bind:open={ctxOpen}
							touched={ctxTouched}
							onPatch={patchCtx}
							sections={CTX_MODAL_SECTIONS}
						/>
					{/if}
				</div>
			</ScrollArea>

			<Separator />

			<div class="flex items-center justify-end gap-3 bg-muted/30 p-4">
				{#if ctxValidation}
					<span class="mr-auto text-xs text-muted-foreground">{ctxValidation.message}</span>
				{/if}
				<Button variant="outline" onclick={cancelNewContext} disabled={savingContext}>Cancel</Button
				>
				<Button
					onclick={createAndUseContext}
					disabled={!ctxDraft?.name.trim() || savingContext}
					class="gap-2"
				>
					{#if savingContext}
						<Spinner class="h-4 w-4" />
						Creating…
					{:else}
						<Plus class="h-4 w-4" />
						Create & use
					{/if}
				</Button>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
