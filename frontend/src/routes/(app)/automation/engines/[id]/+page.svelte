<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/state';
	import { goto, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import X from '@lucide/svelte/icons/x';
	import Code2 from '@lucide/svelte/icons/code-2';
	import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
	import PanelRightOpen from '@lucide/svelte/icons/panel-right-open';
	import Search from '@lucide/svelte/icons/search';
	import Copy from '@lucide/svelte/icons/copy';
	import Download from '@lucide/svelte/icons/download';
	import WandSparkles from '@lucide/svelte/icons/wand-sparkles';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import Workflow from '@lucide/svelte/icons/workflow';
	import GitCompare from '@lucide/svelte/icons/git-compare';
	import Layers from '@lucide/svelte/icons/layers';

	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Toggle } from '$lib/components/ui/toggle';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Empty from '$lib/components/ui/empty';
	import * as Resizable from '$lib/components/ui/resizable';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';

	import EngineTopbar from '$lib/components/engines/engine-topbar.svelte';
	import EngineSummaryBar from '$lib/components/engines/engine-summary-bar.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import StageRow from '$lib/components/engines/stage-row.svelte';
	import YamlPane from '$lib/components/yaml-editor.svelte';
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
	import type { IconComponent } from '$lib/config/icons';
	import { downloadBlob } from '$lib/utilities/download';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { phaseLabel } from '$lib/types/scan-engine';
	import type {
		Intensity,
		ScanEngine,
		StageCatalogEntry,
		StageConfig
	} from '$lib/types/scan-engine';
	import type { PreviewPhase } from '$lib/types/scan';
	import {
		engineToYaml,
		parse,
		validate,
		formatYaml,
		setStageField as yamlSetStageField,
		deleteStage as yamlDeleteStage,
		pruneEmptyStages,
		draftFromDoc,
		overridesOf,
		stageAtOffset,
		type YamlIssue
	} from '$lib/utilities/engine-yaml';

	const PREVIEW_DEBOUNCE_MS = 250;

	type SideTab = 'yaml' | 'pipeline' | 'resolved' | 'diff';
	const SIDE_TABS: { key: SideTab; label: string; icon: IconComponent }[] = [
		{ key: 'yaml', label: 'engine.yaml', icon: Code2 },
		{ key: 'pipeline', label: 'Pipeline', icon: Workflow },
		{ key: 'resolved', label: 'Resolved', icon: Layers },
		{ key: 'diff', label: 'Diff', icon: GitCompare }
	];

	const engineId = $derived(page.params.id);
	const isNarrow = new IsMobile(1100);

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
	let sideTab = $state<SideTab>('yaml');
	let mobileView = $state<'stages' | 'code'>('stages');
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);
	let filter = $state('');
	let modifiedOnly = $state(false);
	let activeStage = $state<string | null>(null);
	let revealToken = $state(0);

	let lensTargetType = $state('domain');
	let previewPhases = $state<PreviewPhase[]>([]);
	let resolvedStages = $state<Record<string, StageConfig>>({});
	let previewWarnings = $state<string[]>([]);
	let previewLoading = $state(false);
	let previewError = $state<string | null>(null);

	const catalog = $derived(engineCatalogStore.catalog);
	const catalogStages = $derived(engineCatalogStore.stages);
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

	const stageStates = $derived(
		Object.fromEntries(
			catalogStages.map((s) => [
				s.name,
				Boolean(parsed?.stages?.[s.name]?.enabled ?? s.defaults.enabled)
			])
		)
	);

	const modifiedCount = $derived(
		catalogStages.filter(
			(s) => Object.keys(overridesOf(parsed?.stages?.[s.name] ?? {}, s.defaults)).length > 0
		).length
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

	const visibleGroups = $derived(stagesByPhase.filter((g) => g.stages.length > 0));

	function levelsOf(stages: StageCatalogEntry[]): StageCatalogEntry[][] {
		const out: StageCatalogEntry[][] = [];
		for (const stage of stages) {
			const last = out[out.length - 1];
			if (last && last[0].level === stage.level) last.push(stage);
			else out.push([stage]);
		}
		return out;
	}

	type RailKind = 'none' | 'solid' | 'dotted';

	function railKinds(
		si: number,
		level: StageCatalogEntry[],
		li: number,
		levels: StageCatalogEntry[][],
		gi: number,
		groups: number
	): { up: RailKind; down: RailKind } {
		const up = si > 0 ? 'solid' : li > 0 || gi > 0 ? 'dotted' : 'none';
		const down =
			si < level.length - 1
				? 'solid'
				: li < levels.length - 1 || gi < groups - 1
					? 'dotted'
					: 'none';
		return { up, down };
	}

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

	function toggleStageFromGutter(stageName: string) {
		const current = stageStates[stageName] ?? true;
		editDoc((d) => yamlSetStageField(d, stageName, 'enabled', !current));
		activeStage = stageName;
	}

	function resetStage(stageName: string) {
		editDoc((d) => yamlDeleteStage(d, stageName));
		activeStage = stageName;
	}

	function flashStage(stageName: string) {
		activeStage = stageName;
		revealToken++;
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
			loadError = e instanceof Error ? e.message : 'Engine could not be loaded';
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
			saveError = 'Enter an engine name before saving.';
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
				saveError = scanEnginesStore.error ?? 'Engine could not be saved';
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

	async function handleCopyYaml() {
		const ok = await writeClipboard(yamlSource);
		if (ok) toast.success('YAML copied');
		else toast.error('Copy failed');
	}

	function handleFormatYaml() {
		const next = formatYaml(yamlSource);
		if (next === yamlSource) toast.message('Already formatted');
		else yamlSource = next;
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

	function setSideTab(value: string) {
		sideTab = value as SideTab;
		localStorage.setItem(STORAGE_KEYS.engineSideTab, sideTab);
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
		const storedTab = localStorage.getItem(STORAGE_KEYS.engineSideTab);
		if (storedTab && SIDE_TABS.some((t) => t.key === storedTab)) sideTab = storedTab as SideTab;

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

{#snippet controls()}
	<section class="controls">
		<div class="toolbar">
			<InputGroup.Root
				class="h-7 min-w-0 flex-1 rounded-md border-0 bg-transparent shadow-none has-[[data-slot=input-group-control]:focus-visible]:ring-0 dark:bg-transparent"
			>
				<InputGroup.Addon class="text-muted-foreground">
					<Search />
				</InputGroup.Addon>
				<InputGroup.Input
					bind:value={filter}
					placeholder="Filter stages, tools, settings…"
					class="h-7 text-xs"
				/>
			</InputGroup.Root>
			<Toggle
				size="sm"
				variant="outline"
				pressed={modifiedOnly}
				onPressedChange={(v) => (modifiedOnly = v)}
				class="h-7 gap-1.5 px-2 text-[11px]"
				aria-label="Show only modified stages"
			>
				Modified
				{#if modifiedCount}
					<span class="count">{modifiedCount}</span>
				{/if}
			</Toggle>
			{#if !isNarrow.current}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="h-7 w-7 text-muted-foreground"
								onclick={toggleSidePane}
								aria-label="{showSidePane ? 'Hide' : 'Show'} code panel"
							>
								{#if showSidePane}<PanelRightClose size={14} />{:else}<PanelRightOpen
										size={14}
									/>{/if}
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="text-xs"
						>{showSidePane ? 'Hide' : 'Show'} code panel</Tooltip.Content
					>
				</Tooltip.Root>
			{/if}
		</div>

		<ScrollArea class="min-h-0 flex-1">
			<div class="stages">
				{#if !parsed}
					<p class="none">
						The YAML document has a syntax error. Fix it in the editor to restore the stage
						controls.
					</p>
				{:else if visibleGroups.length === 0}
					<p class="none">No stages match.</p>
				{/if}

				{#if parsed}
					{#each visibleGroups as group, gi (group.phase)}
						{@const levels = levelsOf(group.stages)}
						<div class="phase" class:linked={gi > 0}>
							<header class="phase-head">
								{#if gi > 0}
									<span class="dotted phase-link" aria-hidden="true"></span>
								{/if}
								<h2>{phaseLabel(group.phase)}</h2>
								<span class="phase-count">
									{group.stages.filter((s) => stageStates[s.name]).length}/{group.stages.length} on
								</span>
							</header>
							<div class="phase-body">
								{#each levels as level, li (level[0].level)}
									{#if li > 0}
										<Tooltip.Root>
											<Tooltip.Trigger>
												{#snippet child({ props })}
													<div {...props} class="level-gap">
														<span class="dotted" aria-hidden="true"></span>
													</div>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Content side="right" class="text-xs">
												Waits for the stages above to finish
											</Tooltip.Content>
										</Tooltip.Root>
									{/if}
									<div class="level">
										{#each level as stage, si (stage.name)}
											{@const rails = railKinds(si, level, li, levels, gi, visibleGroups.length)}
											<StageRow
												{stage}
												config={stageConfig(stage.name)}
												open={openStages[stage.name] ?? false}
												active={activeStage === stage.name}
												railUp={rails.up}
												railDown={rails.down}
												applicable={stage.applies_to.includes(lensTargetType)}
												blockedByIntensity={blockedByIntensity(stage.name)}
												{lensTargetType}
												onToggleOpen={() => {
													openStages = { ...openStages, [stage.name]: !openStages[stage.name] };
													flashStage(stage.name);
												}}
												onChange={(field, value) => setStageField(stage.name, field, value)}
												onReset={() => resetStage(stage.name)}
											/>
										{/each}
									</div>
								{/each}
							</div>
						</div>
					{/each}
				{/if}
			</div>
		</ScrollArea>
	</section>
{/snippet}

{#snippet side()}
	<section class="side">
		<Tabs.Root value={sideTab} onValueChange={setSideTab} class="side-tabs">
			<div class="side-head">
				<Tabs.List class="h-9 gap-0 rounded-none bg-transparent p-0">
					{#each SIDE_TABS as tab (tab.key)}
						<Tabs.Trigger
							value={tab.key}
							class="h-9 flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 text-xs font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
						>
							<tab.icon size={13} />
							<span class={tab.key === 'yaml' ? 'font-mono' : ''}>{tab.label}</span>
							{#if tab.key === 'yaml' && hasUnsavedChanges}
								<span class="tab-dot" aria-label="Unsaved changes"></span>
							{/if}
						</Tabs.Trigger>
					{/each}
				</Tabs.List>

				{#if sideTab === 'yaml'}
					<div class="side-actions">
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon-sm"
										class="h-7 w-7 text-muted-foreground"
										onclick={handleFormatYaml}
										aria-label="Format document"
									>
										<WandSparkles size={13} />
									</Button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content class="text-xs">Format document</Tooltip.Content>
						</Tooltip.Root>
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon-sm"
										class="h-7 w-7 text-muted-foreground"
										onclick={handleCopyYaml}
										aria-label="Copy YAML"
									>
										<Copy size={13} />
									</Button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content class="text-xs">Copy YAML</Tooltip.Content>
						</Tooltip.Root>
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon-sm"
										class="h-7 w-7 text-muted-foreground"
										onclick={handleExportYaml}
										aria-label="Download YAML"
									>
										<Download size={13} />
									</Button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content class="text-xs">Download .yaml</Tooltip.Content>
						</Tooltip.Root>
					</div>
				{/if}
			</div>

			<Tabs.Content value="yaml" class="side-body">
				<YamlPane
					value={yamlSource}
					saveHint
					{issues}
					{activeStage}
					{stageStates}
					reveal={revealToken}
					onChange={(next) => (yamlSource = next)}
					onCursorMove={handleCursorMove}
					onToggleStage={toggleStageFromGutter}
				/>
			</Tabs.Content>

			<Tabs.Content value="pipeline" class="side-body">
				<EffectPanel
					phases={previewPhases}
					stages={catalogStages}
					isLoading={previewLoading}
					error={previewError}
				/>
			</Tabs.Content>

			<Tabs.Content value="resolved" class="side-body">
				<ResolvedPanel
					resolved={resolvedStages}
					warnings={previewWarnings}
					targetType={lensTargetType}
					isLoading={previewLoading}
					error={previewError}
				/>
			</Tabs.Content>

			<Tabs.Content value="diff" class="side-body">
				<DiffPanel stages={parsed?.stages ?? {}} {catalog} />
			</Tabs.Content>
		</Tabs.Root>
	</section>
{/snippet}

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
				<Empty.Title>Engine could not be loaded</Empty.Title>
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
			{errorCount}
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

		<EngineSummaryBar
			targetType={lensTargetType}
			targetTypes={engineCatalogStore.targetTypes}
			phases={previewPhases}
			warnings={previewWarnings}
			stages={catalogStages}
			isLoading={previewLoading}
			error={previewError}
			onTargetTypeChange={setLensTargetType}
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

		{#if isNarrow.current}
			<div class="mobile-switch">
				<ToggleGroup.Root
					type="single"
					variant="outline"
					size="sm"
					value={mobileView}
					onValueChange={(v) => v && (mobileView = v as 'stages' | 'code')}
					aria-label="Editor view"
				>
					<ToggleGroup.Item value="stages" class="h-7 gap-1.5 px-3 text-xs">
						<SlidersHorizontal size={13} />
						Stages
					</ToggleGroup.Item>
					<ToggleGroup.Item value="code" class="h-7 gap-1.5 px-3 text-xs">
						<Code2 size={13} />
						Code
					</ToggleGroup.Item>
				</ToggleGroup.Root>
			</div>
			<div class="content">
				{#if mobileView === 'stages'}
					{@render controls()}
				{:else}
					{@render side()}
				{/if}
			</div>
		{:else}
			<Resizable.PaneGroup
				direction="horizontal"
				autoSaveId={STORAGE_KEYS.engineSplit}
				class="content"
			>
				<Resizable.Pane defaultSize={52} minSize={32} order={1} class="pane">
					{@render controls()}
				</Resizable.Pane>
				{#if showSidePane}
					<Resizable.Handle class="handle" />
					<Resizable.Pane defaultSize={48} minSize={28} order={2} class="pane">
						{@render side()}
					</Resizable.Pane>
				{/if}
			</Resizable.PaneGroup>
		{/if}

		<LaunchDialog bind:open={showLaunch} presetEngineId={engine.id} />

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
		? `'${draft?.name ?? 'This engine'}' is used by ${engine.usage.schedules} scheduled scan${engine.usage.schedules === 1 ? '' : 's'}. Those schedules will fail to launch without it. Completed scans and their results are unaffected.`
		: `Removes '${draft?.name ?? 'this engine'}' from the project. Completed scans and their results are unaffected.`}
	{isDeleting}
	onOpenChange={(open) => (showDeleteDialog = open)}
	onConfirm={confirmDelete}
/>

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	title="Discard your changes?"
	description="Edits to this engine have not been saved. Leaving now discards them."
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
	:global([data-slot='scroll-area-viewport']:has(.editor) > div) {
		display: block;
		height: 100%;
	}
	:global([data-slot='scroll-area-viewport'] > div > main:has(.editor)) {
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

	.mobile-switch {
		display: flex;
		justify-content: center;
		flex-shrink: 0;
		padding: 6px 12px;
		border-bottom: 1px solid var(--border);
	}

	.editor :global(.content) {
		position: relative;
		display: flex;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}
	.editor :global(.pane) {
		display: flex;
		flex-direction: column;
		min-height: 0;
		min-width: 0;
	}
	.editor :global(.handle) {
		width: 1px;
		background: var(--border);
	}
	.editor :global(.handle[data-active]) {
		background: var(--primary);
	}

	.controls {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
	}

	.toolbar {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
		padding: 5px 8px 5px 6px;
		border-bottom: 1px solid var(--border);
	}
	.count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 16px;
		height: 16px;
		padding: 0 4px;
		border-radius: 999px;
		background: var(--primary);
		color: var(--primary-foreground);
		font-size: 10px;
		font-variant-numeric: tabular-nums;
	}

	.stages {
		max-width: 820px;
		padding: 16px 16px 56px;
	}
	.none {
		font-size: 12px;
		color: var(--muted-foreground);
		padding: 8px 2px;
	}

	.dotted {
		display: block;
		width: 3px;
		background: radial-gradient(
				circle,
				color-mix(in oklch, var(--muted-foreground) 65%, transparent) 1px,
				transparent 1.6px
			)
			center / 3px 5px repeat-y;
	}
	.phase.linked {
		margin-top: 12px;
	}
	.phase-head {
		position: relative;
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 10px;
		padding: 2px 2px 8px 32px;
	}
	.phase-head .phase-link {
		position: absolute;
		left: 15px;
		top: -12px;
		bottom: 0;
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
		position: relative;
		border: 1px solid var(--border);
		border-radius: 0.7rem;
		background: var(--card);
		overflow: hidden;
	}
	.level {
		position: relative;
	}
	.level-gap {
		position: relative;
		height: 14px;
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		background: color-mix(in oklch, var(--muted) 35%, transparent);
	}
	.level-gap .dotted {
		position: absolute;
		left: 15px;
		top: 0;
		bottom: 0;
	}

	.side {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		background: var(--card);
	}
	.side :global(.side-tabs) {
		display: flex;
		flex-direction: column;
		min-height: 0;
		flex: 1;
		gap: 0;
	}
	.side-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		flex-shrink: 0;
		padding: 0 6px 0 4px;
		border-bottom: 1px solid var(--border);
	}
	.side-actions {
		display: flex;
		align-items: center;
		gap: 1px;
	}
	.side :global(.side-body) {
		flex: 1;
		min-height: 0;
		overflow: hidden;
		margin: 0;
	}
	.tab-dot {
		display: inline-block;
		width: 6px;
		height: 6px;
		border-radius: 999px;
		background: var(--primary);
	}
</style>
