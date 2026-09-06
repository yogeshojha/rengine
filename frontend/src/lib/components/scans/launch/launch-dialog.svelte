<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import CornerDownLeft from '@lucide/svelte/icons/corner-down-left';
	import Play from '@lucide/svelte/icons/play';
	import X from '@lucide/svelte/icons/x';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Kbd from '$lib/components/ui/kbd';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansApi } from '$lib/api/scans';
	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { targetsApi } from '$lib/api/targets';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import type { PreviewPhase, ScanPreview, ScanRead } from '$lib/types/scan';
	import type { Target } from '$lib/types/target';
	import { mostRecentEngine, readLastPlan, rememberLastPlan } from '$lib/utilities/launch-plan';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { stagesForDimension } from '$lib/utilities/rechecks';
	import { LaunchState, type RescanSeed } from './launch-state.svelte';
	import { chipFor, INVALID_TARGET_MESSAGE, resolveTargetValue, TARGET_FORMATS } from './targets';
	import TargetPicker from './target-picker.svelte';
	import PlanPicker from './plan-picker.svelte';
	import LaunchSummary from './launch-summary.svelte';
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
	let saveOpen = $state(false);
	let whatRunsOpen = $state(false);
	let previewSeq = 0;
	let planRestored = false;

	let project = $derived(projectsStore.activeProject);
	let enginesReady = $derived(
		(scanEnginesStore.fetchedProjectId === project?.id || !!scanEnginesStore.error) &&
			!scanEnginesStore.isLoading
	);
	let catalogReady = $derived(engineCatalogStore.hasFetched || !!engineCatalogStore.error);
	let busy = $derived(launching || targetsLoading);
	let firstTarget = $derived(launch.targets[0] ?? null);
	let launchLabel = $derived(
		launch.rescan
			? `Rescan ${launch.rescan.assets.length} ${launch.rescan.assets.length === 1 ? 'asset' : 'assets'}`
			: launch.targets.length > 1
				? `Start ${launch.targets.length} scans`
				: 'Start scan'
	);
	let canSaveEngine = $derived(
		!launch.rescan && launch.mode === 'quick' && !!launch.catalog && launch.runningStages.length > 0
	);
	// the engine pipeline shows what the engine decides, not what the target type rules out
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

	$effect(() => {
		if (!open) return;
		const p = project;
		if (!p) return;
		untrack(() => {
			planRestored = false;
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
		if (!open || planRestored || !enginesReady || !catalogReady) return;
		if (rescan && !rechecks.schema) return;
		planRestored = true;
		untrack(() => (rescan ? startRescan(rescan) : restorePlan()));
	});

	function startRescan(seed: Omit<RescanSeed, 'rescannable'>) {
		const schema = rechecks.schema;
		launch.beginRescan(
			{ ...seed, rescannable: schema?.rescannable_stages ?? [] },
			stagesForDimension(schema, seed.dimension)
		);
	}

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

	// without a target the engine is previewed through the type lens alone
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
					global_threads: engine.global_threads,
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
		const exists = (id: string) => scanEnginesStore.engines.some((e) => e.id === id);
		if (rerun) {
			launch.restoreRun(rerun, exists);
		} else if (presetEngineId && exists(presetEngineId)) {
			launch.applyEngine(presetEngineId);
		} else {
			const last = readLastPlan();
			const engineId =
				last?.engineId && exists(last.engineId)
					? last.engineId
					: (mostRecentEngine(scanEnginesStore.engines)?.id ?? null);
			if (last) launch.rememberQuick(last.stages, last.intensity);
			if (engineId) launch.applyEngine(engineId);
			else launch.useQuick();
			if (last?.contextId && scanContextsStore.contexts.some((c) => c.id === last.contextId)) {
				launch.contextId = last.contextId;
			}
		}
		if (presetContextId) launch.contextId = presetContextId;
	}

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
					toast.warning(
						`${unresolved} ${unresolved === 1 ? 'target' : 'targets'} could not be loaded.`
					);
				}
			}
			for (const value of values) {
				const chip = await resolveTargetValue(value, projectSlug);
				if (chip) launch.addTarget(chip);
				else toast.error(`${INVALID_TARGET_MESSAGE}: ${value}. ${TARGET_FORMATS}`);
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Targets could not be loaded');
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
				toast.error(scansStore.error ?? 'Scan could not be started');
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
					? `Scan queued for ${created[0].execution_config.target_value}`
					: `${created.length} scans queued`
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
			await rechecks.rescan(projectId, body);
			const n = body.assets.length;
			toast.success(`Rechecking ${n} ${n === 1 ? 'asset' : 'assets'}`, {
				description: 'Results appear as the scan produces them.'
			});
			close();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Rescan could not start');
		}
	}

	function close() {
		open = false;
		onClose?.();
	}

	function handleOpenChange(next: boolean) {
		if (!next) close();
		else open = true;
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

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content
		class="flex max-h-[92vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-[680px]"
		onkeydown={handleKeydown}
	>
		{#if view === 'launch'}
			<Dialog.Header class="px-6 pt-6 pb-0">
				<Dialog.Title>{launch.rescan ? 'Rescan' : 'New scan'}</Dialog.Title>
				<Dialog.Description class="sr-only">
					{launch.rescan
						? 'Choose what to re-run against the selected assets.'
						: 'Choose targets and a configuration, then start the scan.'}
				</Dialog.Description>
			</Dialog.Header>

			<ScrollArea
				class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-10rem)]"
			>
				<div class="flex flex-col gap-5 px-6 pt-5 pb-4">
					{#if launch.rescan}
						<div class="flex flex-col gap-2">
							<Label>
								Assets
								<span class="ml-1 font-normal text-muted-foreground">
									from the run that found them
								</span>
							</Label>
							<div
								class="flex max-h-32 flex-wrap gap-1.5 overflow-y-auto rounded-md border bg-muted/20 p-2"
							>
								{#each launch.rescan.assets as asset (asset)}
									<span
										class="inline-flex items-center gap-1.5 rounded-md border bg-background py-0.5 pr-1 pl-2 font-mono text-xs"
									>
										{asset}
										<button
											type="button"
											class="rounded-sm px-0.5 text-muted-foreground hover:text-foreground"
											aria-label="Remove {asset}"
											disabled={launching}
											onclick={() => launch.removeAsset(asset)}
										>
											<X class="size-3" />
										</button>
									</span>
								{/each}
							</div>
						</div>
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

					<PlanPicker
						{launch}
						phases={enginePipeline}
						phasesLoading={previewLoading || enginePhasesLoading}
						disabled={launching}
						onClose={close}
					/>

					<LaunchContextField
						{launch}
						disabled={launching}
						onNewContext={() => (view = 'newContext')}
					/>

					<LaunchSummary {launch} {preview} {previewLoading} bind:open={whatRunsOpen} />
				</div>
			</ScrollArea>

			<Separator />

			<div class="flex items-center gap-2 bg-muted/30 px-4 py-4 sm:gap-3 sm:px-6">
				{#if canSaveEngine}
					<Button
						variant="ghost"
						size="sm"
						class="hidden text-muted-foreground sm:inline-flex"
						onclick={() => (saveOpen = true)}
						disabled={busy}
					>
						Save as scan engine
					</Button>
				{/if}
				<span class="flex-1"></span>
				{#if launch.blockReason && launch.catalog}
					<span class="hidden text-xs text-muted-foreground sm:inline">{launch.blockReason}</span>
				{/if}
				<Button variant="outline" onclick={close} disabled={launching}>Cancel</Button>
				<Button onclick={handleLaunch} disabled={!launch.canLaunch || busy} class="min-w-0 gap-2">
					{#if launching}
						<Spinner class="size-4" />
						Queuing
					{:else}
						<Play class="size-4" />
						<span>{launchLabel}</span>
						{#if launch.canLaunch}
							<Kbd.Root class="bg-primary-foreground/20 text-primary-foreground">
								<CornerDownLeft class="size-3" />
							</Kbd.Root>
						{/if}
					{/if}
				</Button>
			</div>
		{:else}
			<LaunchContextForm
				targetValue={firstTarget?.value ?? ''}
				onBack={() => (view = 'launch')}
				onCreated={(id, name) => {
					launch.contextId = id;
					view = 'launch';
					toast.success(`Context "${name}" created and applied to this scan`);
				}}
			/>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<SaveEngineDialog
	bind:open={saveOpen}
	{launch}
	suggestedName={preview?.engine_name ?? ''}
	onSaved={(engine) => {
		launch.applyEngine(engine.id);
		toast.success(`Engine "${engine.name}" saved`);
	}}
/>
