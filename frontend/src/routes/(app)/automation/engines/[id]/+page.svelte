<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/state';
	import { goto, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import X from '@lucide/svelte/icons/x';
	import Code2 from '@lucide/svelte/icons/code-2';
	import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Search from '@lucide/svelte/icons/search';

	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Toggle } from '$lib/components/ui/toggle';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Empty from '$lib/components/ui/empty';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';

	import EngineTopbar from '$lib/components/engines/engine-topbar.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import StageRow from '$lib/components/engines/stage-row.svelte';
	import YamlPane from '$lib/components/engines/yaml-pane.svelte';
	import EffectPanel from '$lib/components/engines/effect-panel.svelte';
	import ResolvedPanel from '$lib/components/engines/resolved-panel.svelte';
	import DiffPanel from '$lib/components/engines/diff-panel.svelte';
	import ToolOptionsPanel from '$lib/components/engines/tool-options-panel.svelte';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { IsMobile } from '$lib/hooks/is-mobile.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { downloadBlob } from '$lib/utilities/download';
	import { phaseLabel } from '$lib/types/scan-engine';
	import type { Intensity, ScanEngine, StageConfig } from '$lib/types/scan-engine';
	import type { PreviewPhase } from '$lib/types/scan';
	import {
		engineToYaml,
		parse,
		validate,
		setStageField as yamlSetStageField,
		deleteStage as yamlDeleteStage,
		pruneEmptyStages,
		draftFromDoc,
		overridesOf,
		stageRange,
		stageAtOffset,
		type YamlIssue
	} from '$lib/utilities/engine-yaml';

	const PREVIEW_DEBOUNCE_MS = 250;

	const engineId = $derived(page.params.id);
	const isNarrow = new IsMobile(1180);

	let engine = $state<ScanEngine | null>(null);
	let yamlSource = $state('');
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let saveError = $state<string | null>(null);

	let openStages = $state<Record<string, boolean>>({});
	let showToolOptions = $state(false);
	let showLaunch = $state(false);
	let pendingToolOptions = $state<Record<string, string> | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let showLeaveDialog = $state(false);
	let showSidePane = $state(true);
	let sideTab = $state<'yaml' | 'pipeline' | 'resolved' | 'diff'>('yaml');
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);
	let filter = $state('');
	let modifiedOnly = $state(false);
	let focusRange = $state<[number, number] | null>(null);
	let activeStage = $state<string | null>(null);

	let lensTargetType = $state('domain');
	let previewPhases = $state<PreviewPhase[]>([]);
	let resolvedStages = $state<Record<string, StageConfig>>({});
	let previewWarnings = $state<string[]>([]);
	let previewLoading = $state(false);
	let previewError = $state<string | null>(null);

	const catalog = $derived(engineCatalogStore.catalog);
	const doc = $derived(yamlSource ? parse(yamlSource) : null);
	const issues = $derived<YamlIssue[]>(doc ? validate(yamlSource, doc, catalog) : []);
	const errorCount = $derived(issues.filter((i) => i.severity === 'error').length);
	const parsed = $derived(doc && !doc.errors.length ? draftFromDoc(doc) : null);

	const draft = $derived.by<ScanEngine | null>(() => {
		if (!engine || !parsed) return null;
		return {
			...engine,
			name: parsed.name,
			description: parsed.description,
			intensity: parsed.intensity as Intensity,
			global_threads: parsed.global_threads,
			stages: parsed.stages
		};
	});

	const savedYaml = $derived(engine ? (engine.yaml_source ?? engineToYaml(engine, catalog)) : '');
	const hasUnsavedChanges = $derived(
		Boolean(engine) &&
			Boolean(yamlSource) &&
			(yamlSource !== savedYaml || pendingToolOptions !== null)
	);

	const stagesByPhase = $derived.by(() => {
		const term = filter.trim().toLowerCase();
		return engineCatalogStore.byPhase().map((group) => ({
			phase: group.phase,
			stages: group.stages.filter((stage) => {
				if (
					modifiedOnly &&
					!Object.keys(overridesOf(parsed?.stages?.[stage.name] ?? {}, stage.defaults)).length
				) {
					return false;
				}
				if (!term) return true;
				return (
					stage.title.toLowerCase().includes(term) ||
					stage.name.includes(term) ||
					stage.tools.some((t) => t.includes(term)) ||
					stage.fields.some((f) => f.name.includes(term) || f.title.toLowerCase().includes(term))
				);
			})
		}));
	});

	const visibleCount = $derived(stagesByPhase.reduce((n, g) => n + g.stages.length, 0));

	function stageConfig(name: string): StageConfig {
		return parsed?.stages?.[name] ?? {};
	}

	function blockedByIntensity(stageName: string): boolean {
		if (parsed?.intensity !== 'passive') return false;
		return engineCatalogStore.stage(stageName)?.touches_target ?? false;
	}

	function editDoc(mutate: (d: ReturnType<typeof parse>) => void) {
		if (!yamlSource) return;
		const next = parse(yamlSource);
		mutate(next);
		pruneEmptyStages(next);
		yamlSource = String(next);
	}

	function setStageField(stageName: string, field: string, value: unknown) {
		editDoc((d) => yamlSetStageField(d, stageName, field, value));
		flashStage(stageName);
	}

	function resetStage(stageName: string) {
		editDoc((d) => yamlDeleteStage(d, stageName));
		activeStage = stageName;
		focusRange = null;
	}

	function flashStage(stageName: string) {
		activeStage = stageName;
		focusRange = yamlSource ? stageRange(parse(yamlSource), stageName) : null;
	}

	function handleCursorMove(offset: number) {
		if (!doc) return;
		const hit = stageAtOffset(doc, offset);
		if (hit && hit !== activeStage) activeStage = hit;
	}

	$effect(() => {
		engineCatalogStore.fetch();
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = engineId;
		if (!project || !id) return;
		if (id === 'new') {
			untrack(() => goto(ROUTES.engines, { replaceState: true }));
			return;
		}
		untrack(() => loadEngine(id, project.id));
	});

	$effect(() => {
		const ready = engineCatalogStore.hasFetched;
		const loaded = engine;
		untrack(() => {
			if (ready && loaded && !yamlSource) {
				yamlSource = loaded.yaml_source ?? engineToYaml(loaded, engineCatalogStore.catalog);
			}
		});
	});

	$effect(() => {
		const stages = parsed?.stages;
		const intensity = parsed?.intensity;
		const threads = parsed?.global_threads;
		const target = lensTargetType;
		if (!stages || !engineCatalogStore.hasFetched) return;
		const timer = setTimeout(
			() => refreshPreview(target, intensity as Intensity, threads!, stages),
			PREVIEW_DEBOUNCE_MS
		);
		return () => clearTimeout(timer);
	});

	let previewToken = 0;
	async function refreshPreview(
		target_type: string,
		intensity: Intensity,
		global_threads: number,
		stages: Record<string, StageConfig>
	) {
		const token = ++previewToken;
		previewLoading = true;
		previewError = null;
		try {
			const result = await scanEnginesApi.preview({
				target_type,
				intensity,
				global_threads,
				stages
			});
			if (token === previewToken) {
				previewPhases = result.phases;
				resolvedStages = result.resolved_stages;
				previewWarnings = result.warnings;
			}
		} catch (e) {
			if (token === previewToken) {
				previewError = e instanceof Error ? e.message : 'Preview unavailable';
			}
		} finally {
			if (token === previewToken) previewLoading = false;
		}
	}

	async function loadEngine(id: string, projectId: string) {
		isLoading = true;
		loadError = null;
		try {
			const fresh = await scanEnginesApi.get(id, projectId);
			engine = fresh;
			if (!yamlSource && engineCatalogStore.hasFetched) {
				yamlSource = fresh.yaml_source ?? engineToYaml(fresh, engineCatalogStore.catalog);
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load engine';
		} finally {
			isLoading = false;
		}
	}

	async function handleSave() {
		if (!draft || isSaving) return;
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}
		if (errorCount) {
			saveError = `Fix ${errorCount} error${errorCount === 1 ? '' : 's'} before saving.`;
			toast.error(saveError);
			return;
		}
		if (!draft.name.trim()) {
			saveError = 'Give the engine a name before saving.';
			toast.error(saveError);
			return;
		}

		isSaving = true;
		saveError = null;
		try {
			const updated = await scanEnginesStore.updateEngine(draft.id, project.id, {
				name: draft.name,
				description: draft.description,
				intensity: draft.intensity,
				global_threads: draft.global_threads,
				stages: draft.stages,
				yaml_source: yamlSource,
				tool_options: pendingToolOptions ?? draft.tool_options
			});
			if (updated) {
				engine = updated;
				pendingToolOptions = null;
				toast.success('Engine saved');
			} else {
				saveError = scanEnginesStore.error ?? 'Failed to save engine';
				toast.error(saveError);
			}
		} finally {
			isSaving = false;
		}
	}

	function setIntensity(intensity: Intensity) {
		editDoc((d) => d.set('intensity', intensity));
	}

	function setName(name: string) {
		editDoc((d) => d.set('name', name));
	}

	function setToolOptions(tool_options: Record<string, string>) {
		if (engine) engine = { ...engine, tool_options };
		pendingToolOptions = tool_options;
	}

	function handleExportYaml() {
		downloadBlob(`${draft?.name || 'engine'}.yaml`, yamlSource, 'text/yaml');
		toast.success('YAML exported');
	}

	async function handleDuplicate() {
		const project = projectsStore.activeProject;
		if (!project || !draft) return;
		const copy = await scanEnginesStore.duplicateEngine(draft.id, project.id);
		if (copy?.id) {
			toast.success(`Duplicated as "${copy.name}"`);
			allowNavigation = true;
			goto(ROUTES.engine(copy.id));
		} else {
			toast.error(scanEnginesStore.error ?? 'Duplicate failed');
		}
	}

	async function confirmDelete() {
		if (!draft) return;
		isDeleting = true;
		try {
			const ok = await scanEnginesStore.deleteEngine(draft.id);
			if (ok) {
				toast.success('Engine deleted');
				showDeleteDialog = false;
				allowNavigation = true;
				goto(ROUTES.engines);
			} else {
				toast.error(scanEnginesStore.error ?? 'Delete failed');
			}
		} finally {
			isDeleting = false;
		}
	}

	function toggleSidePane() {
		showSidePane = !showSidePane;
		localStorage.setItem(STORAGE_KEYS.engineSidePane, String(showSidePane));
	}

	function setLensTargetType(value: string) {
		lensTargetType = value;
		localStorage.setItem(STORAGE_KEYS.engineLensTargetType, value);
	}

	beforeNavigate((nav) => {
		if (allowNavigation) {
			allowNavigation = false;
			return;
		}
		if (!hasUnsavedChanges || pendingNav) return;
		nav.cancel();
		pendingNav = () => {
			allowNavigation = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	onMount(() => {
		const storedLens = localStorage.getItem(STORAGE_KEYS.engineLensTargetType);
		if (storedLens) lensTargetType = storedLens;
		const storedPane = localStorage.getItem(STORAGE_KEYS.engineSidePane);
		if (storedPane !== null) showSidePane = storedPane === 'true';

		const onKey = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === 's') {
				e.preventDefault();
				handleSave();
			}
		};
		const onBeforeUnload = (e: BeforeUnloadEvent) => {
			if (!hasUnsavedChanges) return;
			e.preventDefault();
			e.returnValue = '';
		};
		window.addEventListener('keydown', onKey);
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => {
			window.removeEventListener('keydown', onKey);
			window.removeEventListener('beforeunload', onBeforeUnload);
		};
	});
</script>

<div class="editor">
	{#if isLoading && !engine}
		<div class="state">
			<Spinner size={20} class="text-muted-foreground" />
			<span class="text-sm text-muted-foreground">Loading engine…</span>
		</div>
	{:else if loadError}
		<Empty.Root class="flex-1">
			<Empty.Header>
				<Empty.Media class="size-[52px] rounded-xl bg-destructive/10">
					<AlertTriangle size={22} class="text-destructive" />
				</Empty.Media>
				<Empty.Title>Failed to load engine</Empty.Title>
				<Empty.Description>{loadError}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button onclick={() => goto(ROUTES.engines)}>Back to engines</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if engine}
		<EngineTopbar
			engine={draft ?? engine}
			{isSaving}
			{hasUnsavedChanges}
			onSave={handleSave}
			onNameChange={setName}
			onIntensityChange={setIntensity}
			onToolOptions={() => (showToolOptions = true)}
			onRun={() => (showLaunch = true)}
			onBack={() => goto(ROUTES.engines)}
			onDuplicate={handleDuplicate}
			onDelete={() => (showDeleteDialog = true)}
			onExportYaml={handleExportYaml}
		/>

		{#if saveError}
			<div class="save-error" role="alert">
				<AlertTriangle size={13} class="shrink-0" />
				<span class="flex-1 truncate">{saveError}</span>
				<Button
					variant="ghost"
					size="icon-sm"
					class="h-6 w-6"
					aria-label="Dismiss"
					onclick={() => (saveError = null)}
				>
					<X size={13} />
				</Button>
			</div>
		{/if}

		<div class="content">
			<section class="controls" class:solo={!showSidePane}>
				<div class="toolbar">
					<div class="search">
						<Search size={13} class="search-icon" />
						<Input
							bind:value={filter}
							placeholder="Filter settings…"
							class="h-7 border-0 bg-transparent pl-7 text-xs shadow-none focus-visible:ring-0"
						/>
					</div>
					<Toggle
						size="sm"
						pressed={modifiedOnly}
						onPressedChange={(v) => (modifiedOnly = v)}
						class="h-7 px-2 text-[11px]"
						aria-label="Show only modified settings"
					>
						Modified
					</Toggle>
					{#if true}
						<Button
							variant="ghost"
							size="sm"
							class="h-7 gap-1.5 px-2 text-[11px]"
							onclick={toggleSidePane}
						>
							{#if showSidePane}<PanelRightClose size={13} />{:else}<Code2 size={13} />{/if}
							{showSidePane ? 'Hide' : 'Show'} panel
						</Button>
					{/if}
				</div>

				<ScrollArea class="min-h-0 flex-1">
					<div class="stages">
						{#if !parsed}
							<p class="none">
								The YAML has a syntax error. Fix it in the editor to get the controls back.
							</p>
						{:else if visibleCount === 0}
							<p class="none">No stages match.</p>
						{/if}

						{#each stagesByPhase as group (group.phase)}
							{#if group.stages.length && parsed}
								<div class="phase">
									<header class="phase-head">
										<h2>{phaseLabel(group.phase)}</h2>
										<span class="phase-count">
											{group.stages.filter((s) => stageConfig(s.name).enabled ?? s.defaults.enabled)
												.length}/{group.stages.length} on
										</span>
									</header>
									<div class="phase-body">
										{#each group.stages as stage (stage.name)}
											<div class="row-wrap" class:active={activeStage === stage.name}>
												<StageRow
													{stage}
													config={stageConfig(stage.name)}
													open={openStages[stage.name] ?? false}
													applicable={true}
													blockedByIntensity={blockedByIntensity(stage.name)}
													lensTargetType={null}
													onToggleOpen={() => {
														openStages = {
															...openStages,
															[stage.name]: !openStages[stage.name]
														};
														flashStage(stage.name);
													}}
													onChange={(field, value) => setStageField(stage.name, field, value)}
													onReset={() => resetStage(stage.name)}
												/>
											</div>
										{/each}
									</div>
								</div>
							{/if}
						{/each}
					</div>
				</ScrollArea>
			</section>

			{#if showSidePane}
				<section class="side" class:narrow={isNarrow.current}>
					<Tabs.Root
						value={sideTab}
						onValueChange={(v) => (sideTab = v as 'yaml' | 'pipeline')}
						class="side-tabs"
					>
						<div class="side-head">
							<Tabs.List class="h-7">
								<Tabs.Trigger value="yaml" class="gap-1.5 px-2.5 text-[11px]">
									<Code2 size={12} />
									engine.yaml
								</Tabs.Trigger>
								<Tabs.Trigger value="pipeline" class="px-2.5 text-[11px]">Pipeline</Tabs.Trigger>
								<Tabs.Trigger value="resolved" class="px-2.5 text-[11px]">Resolved</Tabs.Trigger>
								<Tabs.Trigger value="diff" class="px-2.5 text-[11px]">Diff</Tabs.Trigger>
							</Tabs.List>
							{#if sideTab === 'yaml'}
								{#if errorCount}
									<span class="status err">
										<AlertTriangle size={11} />
										{errorCount} error{errorCount === 1 ? '' : 's'}
									</span>
								{:else}
									<span class="status ok"><CircleCheck size={11} /> valid</span>
								{/if}
							{/if}
						</div>

						<Tabs.Content value="yaml" class="side-body">
							<YamlPane
								value={yamlSource}
								{issues}
								highlight={focusRange}
								onChange={(next) => (yamlSource = next)}
								onCursorMove={handleCursorMove}
							/>
						</Tabs.Content>

						<Tabs.Content value="resolved" class="side-body">
							<ResolvedPanel
								resolved={resolvedStages}
								warnings={previewWarnings}
								targetType={lensTargetType}
								targetTypes={engineCatalogStore.targetTypes}
								isLoading={previewLoading}
								error={previewError}
								onTargetTypeChange={setLensTargetType}
							/>
						</Tabs.Content>

						<Tabs.Content value="diff" class="side-body">
							<DiffPanel stages={parsed?.stages ?? {}} catalog={engineCatalogStore.catalog} />
						</Tabs.Content>

						<Tabs.Content value="pipeline" class="side-body">
							<EffectPanel
								phases={previewPhases}
								targetType={lensTargetType}
								targetTypes={engineCatalogStore.targetTypes}
								isLoading={previewLoading}
								error={previewError}
								onTargetTypeChange={setLensTargetType}
							/>
						</Tabs.Content>
					</Tabs.Root>
				</section>
			{/if}
		</div>

		<LaunchModal bind:open={showLaunch} presetEngineId={engine.id} />

		<ToolOptionsPanel
			open={showToolOptions}
			toolOptions={draft?.tool_options ?? {}}
			tools={engineCatalogStore.toolOptions}
			onOpenChange={(o) => (showToolOptions = o)}
			onChange={setToolOptions}
		/>
	{/if}
</div>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title="Delete this engine?"
	description={engine?.usage?.schedules
		? `'${draft?.name ?? 'This engine'}' is used by ${engine.usage.schedules} scheduled scan${engine.usage.schedules === 1 ? '' : 's'} — those will stop working. This cannot be undone.`
		: `Delete '${draft?.name ?? 'this engine'}'? This cannot be undone.`}
	{isDeleting}
	onOpenChange={(open) => (showDeleteDialog = open)}
	onConfirm={confirmDelete}
/>

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	title="Discard your changes?"
	description="Your edits to this engine have not been saved."
	confirmLabel="Discard"
	cancelLabel="Keep editing"
	onOpenChange={(o) => {
		showLeaveDialog = o;
		if (!o) pendingNav = null;
	}}
	onConfirm={() => {
		showLeaveDialog = false;
		const resume = pendingNav;
		pendingNav = null;
		allowNavigation = true;
		resume?.();
	}}
/>

<style>
	:global(main:has(.editor)) {
		height: 100%;
		padding: 0;
	}

	.editor {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		overflow: hidden;
	}

	.state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 14px;
		padding: 40px;
		text-align: center;
	}

	.save-error {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
		padding: 5px 12px;
		background: color-mix(in oklch, var(--destructive) 8%, var(--card));
		border-bottom: 1px solid color-mix(in oklch, var(--destructive) 30%, var(--border));
		color: var(--destructive);
		font-size: 12px;
		font-weight: 500;
	}

	.content {
		position: relative;
		display: flex;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	.controls {
		display: flex;
		flex-direction: column;
		min-height: 0;
		min-width: 0;
		flex: 1 1 54%;
		border-right: 1px solid var(--border);
	}
	.controls.solo {
		flex: 1 1 100%;
		border-right: none;
	}

	.toolbar {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
		padding: 6px 10px;
		border-bottom: 1px solid var(--border);
	}
	.search {
		position: relative;
		flex: 1;
		min-width: 0;
	}
	.search :global(.search-icon) {
		position: absolute;
		left: 6px;
		top: 50%;
		transform: translateY(-50%);
		color: var(--muted-foreground);
		pointer-events: none;
		z-index: 1;
	}

	.stages {
		max-width: 760px;
		padding: 16px 16px 48px;
	}
	.none {
		font-size: 12px;
		color: var(--muted-foreground);
		padding: 8px 2px;
	}

	.phase + .phase {
		margin-top: 20px;
	}
	.phase-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 10px;
		padding: 0 2px 7px;
	}
	.phase-head h2 {
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--muted-foreground);
	}
	.phase-count {
		font-size: 11px;
		color: var(--muted-foreground);
		font-variant-numeric: tabular-nums;
	}
	.phase-body {
		border: 1px solid var(--border);
		border-radius: 0.7rem;
		background: var(--card);
		overflow: hidden;
	}

	.row-wrap {
		position: relative;
		transition: background 0.15s ease;
	}
	.row-wrap.active {
		background: color-mix(in oklch, var(--muted) 55%, transparent);
	}
	.row-wrap.active::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 2px;
		background: var(--foreground);
		opacity: 0.4;
	}

	.side.narrow {
		position: absolute;
		inset: 0;
		z-index: 20;
		flex: 1 1 100%;
	}
	.side {
		display: flex;
		flex-direction: column;
		min-height: 0;
		min-width: 0;
		flex: 1 1 46%;
		background: var(--card);
	}
	.side :global(.side-tabs) {
		display: flex;
		flex-direction: column;
		min-height: 0;
		flex: 1;
	}
	.side-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		flex-shrink: 0;
		padding: 5px 10px;
		border-bottom: 1px solid var(--border);
	}
	.side :global(.side-body) {
		flex: 1;
		min-height: 0;
		overflow: hidden;
		margin: 0;
	}
	.status {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 11px;
		padding-right: 2px;
	}
	.status.ok {
		color: var(--muted-foreground);
	}
	.status.err {
		color: var(--destructive);
	}
</style>
