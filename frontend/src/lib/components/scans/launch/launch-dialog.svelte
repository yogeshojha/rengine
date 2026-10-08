<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import CornerDownLeft from '@lucide/svelte/icons/corner-down-left';
	import Info from '@lucide/svelte/icons/info';
	import Play from '@lucide/svelte/icons/play';
	import Hint from '$lib/components/hint.svelte';
	import { Switch } from '$lib/components/ui/switch';
	import { NEW_CHECKS_HELP, NEW_CHECKS_TITLE } from '$lib/config/new-checks';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Kbd from '$lib/components/ui/kbd';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { launchLocked } from '$lib/config/launch';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansApi } from '$lib/api/scans';
	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { targetsApi } from '$lib/api/targets';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import type { PreviewPhase, ScanPreview, ScanRead } from '$lib/types/scan';
	import type { RunPreview } from '$lib/types/recheck';
	import type { Target } from '$lib/types/target';
	import { mostRecentEngine, readLastPlan, rememberLastPlan } from '$lib/utilities/launch-plan';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { runDescription, runStarted, stagesForDimension } from '$lib/utilities/rechecks';
	import { LaunchState, type RescanSeed } from './launch-state.svelte';
	import { chipFor, invalidTargetMessage, resolveTargetValue } from './targets';
	import TargetPicker from './target-picker.svelte';
	import PlanPicker from './plan-picker.svelte';
	import LaunchSummary from './launch-summary.svelte';
	import RescanScope from './rescan-scope.svelte';
	import LaunchContextField from './launch-context-field.svelte';
	import LaunchContextForm from './launch-context-form.svelte';
	import SaveEngineDialog from './save-engine-dialog.svelte';

	interface Props {
		open: boolean;
		targetId?: string;
		targetIds?: string[];
		targetValues?: string[];
		presetEngineId?: string;
		presetContextId?: string;
		rerun?: ScanRead | null;
		rescan?: Omit<RescanSeed, 'rescannable'> | null;
		onClose?: () => void;
	}

	let {
		open = $bindable(),
		targetId,
		targetIds,
		targetValues,
		presetEngineId,
		presetContextId,
		rerun = null,
		rescan = null,
		onClose
	}: Props = $props();

	const PREVIEW_DEBOUNCE_MS = 350;
	const TARGET_PAGE_SIZE = 100;
	const TARGET_FETCH_CONCURRENCY = 10;

	const launch = new LaunchState();

	let view = $state<'launch' | 'newContext'>('launch');
	let targetsLoading = $state(false);
	let preview = $state<ScanPreview | null>(null);
	let previewLoading = $state(false);
	let enginePhases = $state<PreviewPhase[]>([]);
	let enginePhasesLoading = $state(false);
	let enginePreviewSeq = 0;
	let launching = $state(false);
	let runPreview = $state<RunPreview | null>(null);
	let runPreviewLoading = $state(false);
	let runPreviewSeq = 0;
	let saveOpen = $state(false);
	let whatRunsOpen = $state(false);
	let previewSeq = 0;
	let planRestored = false;
	let prefilledFor = '';
	let restored = $state(false);
	let baseline = $state<string | null>(null);
	let contextDirty = $state(false);

	let project = $derived(projectsStore.activeProject);
	let enginesReady = $derived(
		(scanEnginesStore.fetchedProjectId === project?.id || !!scanEnginesStore.error) &&
			!scanEnginesStore.isLoading
	);
	let contextsReady = $derived(
		(scanContextsStore.fetchedProjectId === project?.id || !!scanContextsStore.error) &&
			!scanContextsStore.isLoading
	);
	let catalogReady = $derived(engineCatalogStore.hasFetched || !!engineCatalogStore.error);
	let busy = $derived(launching || targetsLoading);
	let firstTarget = $derived(launch.targets[0] ?? null);
	let launchLabel = $derived.by(() => {
		if (!launch.rescan) {
			return launch.targets.length > 1 ? `Start ${launch.targets.length} scans` : 'Start scan';
		}
		const n = runPreview?.asset_count ?? launch.rescan.assets.length;
		return `Rescan ${n.toLocaleString()} ${n === 1 ? 'asset' : 'assets'}`;
	});
	let suggestedEngineName = $derived.by(() => {
		if (launch.mode !== 'quick') return preview?.engine_name ?? '';
		const n = launch.runningStages.length;
		return `Custom scan · ${n} ${n === 1 ? 'stage' : 'stages'}`;
	});
	let canSaveEngine = $derived(
		!launch.rescan && launch.mode === 'quick' && !!launch.catalog && launch.runningStages.length > 0
	);
	let enginePipeline = $derived(
		(preview?.phases ?? enginePhases).map((phase) => ({
			...phase,
			tools: phase.tools.filter((t) => t.status !== 'skipped_not_applicable')
		}))
	);
	let previewSignature = $derived(
		JSON.stringify([
			launch.engineId,
			launch.overrides,
			launch.intensity,
			launch.contextId,
			firstTarget?.id ?? firstTarget?.value ?? null
		])
	);

	const signature = () =>
		JSON.stringify([
			launch.targets.map((t) => t.key),
			launch.rescan?.assets ?? null,
			launch.mode,
			launch.engineId,
			launch.patch,
			launch.intensity,
			launch.contextId
		]);
	let dirty = $derived(
		open &&
			((baseline !== null && signature() !== baseline) || (view === 'newContext' && contextDirty))
	);
	const guard = new DiscardGuard(() => dirty, close);
	const backGuard = new DiscardGuard(
		() => contextDirty,
		() => (view = 'launch')
	);

	$effect(() => {
		if (!open) return;
		const p = project;
		if (!p) return;
		untrack(() => {
			planRestored = false;
			restored = false;
			baseline = null;
			contextDirty = false;
			prefilledFor = '';
			view = 'launch';
			whatRunsOpen = false;
			preview = null;
			launch.reset();
			if (scanEnginesStore.fetchedProjectId !== p.id) scanEnginesStore.fetchEngines(p.id);
			if (scanContextsStore.fetchedProjectId !== p.id) scanContextsStore.fetchContexts(p.id);
			if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
			if (rescan) void rechecks.loadSchema();
			else loadTargets(p.slug);
		});
	});

	$effect(() => {
		if (!open || planRestored || !enginesReady || !contextsReady || !catalogReady) return;
		if (rescan && !rechecks.schema) return;
		planRestored = true;
		untrack(() => (rescan ? startRescan(rescan) : restorePlan()));
		restored = true;
	});

	$effect(() => {
		if (!open || !restored || targetsLoading || baseline !== null) return;
		baseline = untrack(signature);
	});

	function startRescan(seed: Omit<RescanSeed, 'rescannable'>) {
		const schema = rechecks.schema;
		launch.beginRescan(
			{ ...seed, rescannable: schema?.rescannable_stages ?? [] },
			stagesForDimension(schema, seed.dimension)
		);
	}

	$effect(() => {
		const seed = launch.rescan;
		const p = project;
		if (!open || !seed || !p) {
			runPreview = null;
			runPreviewLoading = false;
			return;
		}
		void JSON.stringify(seed.selection);
		runPreviewLoading = true;
		const seq = ++runPreviewSeq;
		const body = { selection: seed.selection };
		void scansApi
			.rescanPreview(p.id, body)
			.then((r) => {
				if (seq === runPreviewSeq) runPreview = r;
			})
			.catch(() => {
				if (seq === runPreviewSeq) runPreview = null;
			})
			.finally(() => {
				if (seq === runPreviewSeq) runPreviewLoading = false;
			});
	});

	$effect(() => {
		if (!open) return;
		const signature = previewSignature;
		const p = project;
		const target = firstTarget;
		if (!p || !launch.catalog || !target) {
			preview = null;
			previewLoading = false;
			return;
		}
		void signature;
		previewLoading = true;
		const seq = ++previewSeq;
		const timer = setTimeout(async () => {
			try {
				const result = await scansApi.preview(p.id, {
					engine_id: launch.engineId,
					target_id: target.id,
					target_value: target.id ? null : target.value,
					overrides: launch.overrides,
					intensity: launch.intensity,
					context_id: launch.contextId === SELECT_NONE ? null : launch.contextId
				});
				if (seq === previewSeq) preview = result;
			} catch {
				if (seq === previewSeq) preview = null;
			} finally {
				if (seq === previewSeq) previewLoading = false;
			}
		}, PREVIEW_DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	$effect(() => {
		if (!open) return;
		const engine = launch.engine;
		const catalog = launch.catalog;
		const contextId = launch.contextId;
		if (launch.mode !== 'engine' || !engine || !catalog || firstTarget) {
			enginePhases = [];
			enginePhasesLoading = false;
			return;
		}
		enginePhasesLoading = true;
		const seq = ++enginePreviewSeq;
		const timer = setTimeout(async () => {
			try {
				const result = await scanEnginesApi.preview({
					target_type: catalog.target_types[0],
					intensity: engine.intensity,
					stages: engine.stages,
					context_id: contextId === SELECT_NONE ? null : contextId
				});
				if (seq === enginePreviewSeq) enginePhases = result.phases;
			} catch {
				if (seq === enginePreviewSeq) enginePhases = [];
			} finally {
				if (seq === enginePreviewSeq) enginePhasesLoading = false;
			}
		}, PREVIEW_DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	function restorePlan() {
		const exists = (id: string) =>
			scanEnginesStore.engines.some((e) => e.id === id && !launchLocked(e, auth.user));
		const contextExists = (id: string) =>
			scanContextsStore.contexts.some((c) => c.id === id && !launchLocked(c, auth.user));
		if (rerun) {
			launch.restoreRun(rerun, exists, (id) => !!scanContextsStore.error || contextExists(id));
		} else if (presetEngineId && exists(presetEngineId)) {
			launch.applyEngine(presetEngineId);
		} else {
			const last = readLastPlan();
			const engineId =
				last?.engineId && exists(last.engineId)
					? last.engineId
					: (mostRecentEngine(scanEnginesStore.engines.filter((e) => exists(e.id)))?.id ?? null);
			if (last) launch.rememberQuick(last.stages, last.intensity);
			if (engineId) launch.applyEngine(engineId);
			else launch.useQuick();
			if (last?.contextId && contextExists(last.contextId)) launch.contextId = last.contextId;
		}
		if (presetContextId && contextExists(presetContextId)) launch.contextId = presetContextId;
	}

	$effect(() => {
		const only = launch.targets.length === 1 ? launch.targets[0] : null;
		const id = only?.id ?? null;
		if (!id || id === prefilledFor) return;
		prefilledFor = id;
		void targetsApi
			.get(id)
			.then((t) => {
				if (launch.targets.length === 1 && launch.targets[0].id === id) {
					launch.newChecks = t.new_checks;
				}
			})
			.catch(() => undefined);
	});

	async function loadTargets(projectSlug: string) {
		const ids = targetId ? [targetId] : [...(targetIds ?? [])];
		const values = [...(targetValues ?? [])];
		if (!ids.length && !values.length) return;
		targetsLoading = true;
		try {
			if (ids.length) {
				const res = await targetsApi.list({ project_slug: projectSlug, size: TARGET_PAGE_SIZE });
				const known: Record<string, Target> = Object.fromEntries(res.items.map((t) => [t.id, t]));
				const missing = ids.filter((id) => !known[id]);
				for (let i = 0; i < missing.length; i += TARGET_FETCH_CONCURRENCY) {
					const fetched = await Promise.all(
						missing
							.slice(i, i + TARGET_FETCH_CONCURRENCY)
							.map((id) => targetsApi.get(id).catch(() => null))
					);
					for (const t of fetched) if (t) known[t.id] = t;
				}
				let unresolved = 0;
				for (const id of ids) {
					const t = known[id];
					if (t) launch.addTarget(chipFor(t));
					else unresolved += 1;
				}
				if (unresolved) {
					toast.warning(`${unresolved} ${unresolved === 1 ? 'target' : 'targets'} not loaded`);
				}
			}
			for (const value of values) {
				const chip = await resolveTargetValue(value, projectSlug);
				if (chip) launch.addTarget(chip);
				else toast.error(invalidTargetMessage([value]));
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Targets not loaded');
		} finally {
			targetsLoading = false;
		}
	}

	async function handleLaunch() {
		const p = project;
		if (!p || !launch.canLaunch || busy) return;
		launching = true;
		try {
			if (launch.rescan) {
				await launchRescan(p.id);
				return;
			}
			const created = await scansStore.launchScans(p.id, launch.body());
			if (!created) {
				toast.error(scansStore.error ?? 'Scan not started');
				return;
			}
			const previous = readLastPlan();
			const current = launch.stored();
			rememberLastPlan({
				...current,
				engineId: current.mode === 'engine' ? current.engineId : (previous?.engineId ?? null),
				stages: current.mode === 'quick' ? current.stages : (previous?.stages ?? {}),
				intensity: current.mode === 'quick' ? current.intensity : (previous?.intensity ?? null)
			});
			toast.success(
				created.length === 1
					? `Scan started for ${created[0].execution_config.target_value}`
					: `${created.length} scans started`
			);
			close();
			goto(created.length === 1 ? ROUTES.scan(created[0].id) : ROUTES.scans);
		} finally {
			launching = false;
		}
	}

	async function launchRescan(projectId: string) {
		const body = launch.rescanBody();
		if (!body) return;
		try {
			const run = await rechecks.rescan(projectId, body);
			toast.success(runStarted(run, 'asset', 'assets'), { description: runDescription(run) });
			close();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Rescan not started');
		}
	}

	function close() {
		open = false;
		onClose?.();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key !== 'Enter' || e.defaultPrevented || view !== 'launch') return;
		const el = e.target as HTMLElement | null;
		if (el?.closest('button, textarea, [role="option"], [role="menuitem"], [role="listbox"]'))
			return;
		if (!launch.canLaunch || busy) return;
		e.preventDefault();
		handleLaunch();
	}
</script>

<Dialog.Root
	bind:open={
		() => open,
		(next) => {
			if (next) open = true;
			else if (!launching) guard.close();
		}
	}
>
	<Dialog.Content
		class="grid h-[min(90vh,52rem)] grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0 sm:max-w-2xl"
		onkeydown={handleKeydown}
	>
		{#if view === 'launch'}
			<Dialog.Header class="border-b px-6 py-4">
				<Dialog.Title>{launch.rescan ? 'Rescan' : 'New scan'}</Dialog.Title>
				<Dialog.Description class="sr-only">
					{launch.rescan
						? 'Stages to re-run against the selected assets.'
						: 'Targets, configuration and context for a new scan.'}
				</Dialog.Description>
			</Dialog.Header>

			<ScrollArea class="min-h-0">
				<div class="flex flex-col gap-4 px-6 py-5">
					{#if launch.rescan}
						<RescanScope
							assets={launch.rescan.assets}
							queryLabel={launch.rescan.queryLabel}
							preview={runPreview}
							loading={runPreviewLoading}
							disabled={launching}
							onRemove={launch.rescan.selection.picks
								? (asset) => launch.removeAsset(asset)
								: undefined}
						/>
					{:else}
						<div class="flex flex-col gap-2">
							<Label>Targets</Label>
							{#if project}
								<TargetPicker
									chips={launch.targets}
									projectSlug={project.slug}
									disabled={launching}
									loading={targetsLoading}
									onAdd={(chip) => launch.addTarget(chip)}
									onRemove={(key) => launch.removeTarget(key)}
								/>
							{/if}
						</div>
					{/if}

					<LaunchContextField
						{launch}
						disabled={launching}
						onNewContext={() => (view = 'newContext')}
					/>

					<PlanPicker
						{launch}
						phases={enginePipeline}
						phasesLoading={previewLoading || enginePhasesLoading}
						disabled={launching}
						onClose={close}
					/>

					{#if launch.vulnerabilitiesOn}
						<div class="flex items-center gap-2">
							<Switch
								id="launch-new-checks"
								checked={launch.newChecks === true}
								onCheckedChange={(on) => (launch.newChecks = on)}
								disabled={launching}
							/>
							<Label for="launch-new-checks" class="font-normal">{NEW_CHECKS_TITLE}</Label>
							<Hint text={NEW_CHECKS_HELP}>
								{#snippet child(props)}
									<span {...props} class="flex h-5 items-center text-muted-foreground">
										<Info class="size-3.5" />
									</span>
								{/snippet}
							</Hint>
						</div>
					{/if}

					<LaunchSummary {launch} {preview} {previewLoading} bind:open={whatRunsOpen} />
				</div>
			</ScrollArea>

			<div class="flex flex-wrap items-center gap-2 border-t bg-card px-6 py-4 sm:flex-nowrap">
				{#if canSaveEngine}
					<Button
						variant="ghost"
						class="hidden text-muted-foreground sm:inline-flex"
						onclick={() => (saveOpen = true)}
						disabled={busy}
					>
						Save as scan engine
					</Button>
				{/if}
				<span class="flex-1"></span>
				{#if launch.blockReason && launch.catalog}
					<span
						class="order-first basis-full text-xs text-muted-foreground sm:order-none sm:basis-auto"
						>{launch.blockReason}</span
					>
				{/if}
				<Button variant="outline" onclick={() => guard.close()} disabled={launching}>Cancel</Button>
				<LoadingButton
					onclick={handleLaunch}
					disabled={!launch.canLaunch || busy}
					loading={launching}
					loadingLabel="Starting"
					class="min-w-0"
				>
					<Play class="size-4" />
					<span>{launchLabel}</span>
					{#if launch.canLaunch}
						<Kbd.Root class="bg-primary-foreground/20 text-primary-foreground">
							<CornerDownLeft class="size-3" />
						</Kbd.Root>
					{/if}
				</LoadingButton>
			</div>
		{:else}
			<LaunchContextForm
				targetValue={firstTarget?.value ?? ''}
				bind:dirty={contextDirty}
				onBack={backGuard.close}
				onCreated={(id, name) => {
					launch.contextId = id;
					view = 'launch';
					toast.success(`Context "${name}" created`);
				}}
			/>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>

<UnsavedChangesDialog
	open={backGuard.asking}
	onOpenChange={(next) => (backGuard.asking = next)}
	onConfirm={backGuard.discard}
/>

<SaveEngineDialog
	bind:open={saveOpen}
	{launch}
	suggestedName={suggestedEngineName}
	onSaved={(engine) => {
		launch.applyEngine(engine.id);
		toast.success(`Engine "${engine.name}" saved`);
	}}
/>
