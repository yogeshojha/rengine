<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import Upload from '@lucide/svelte/icons/upload';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ListChecks from '@lucide/svelte/icons/list-checks';
	import Search from '@lucide/svelte/icons/search';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import SearchX from '@lucide/svelte/icons/search-x';

	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { NEW_PARAM, ROUTES, routeLabels } from '$lib/config/routes';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as Select from '$lib/components/ui/select';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import EngineListCard from '$lib/components/engines/engine-list-card.svelte';
	import NewEngineDialog from '$lib/components/engines/new-engine-dialog.svelte';
	import ImportEngineDialog from '$lib/components/engines/import-engine-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import { summarize } from '$lib/utilities/engine-summary';
	import { downloadBlob } from '$lib/utilities/download';
	import type { EnginePreset, ScanEngine } from '$lib/types/scan-engine';

	type SortKey = 'recent' | 'name' | 'usage';
	const SORT_LABELS: Record<SortKey, string> = {
		recent: 'Recently used',
		name: 'Name',
		usage: 'Most used'
	};

	let isRefreshing = $state(false);
	let engineToDelete = $state<ScanEngine | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	const selectedIds = new SvelteSet<string>();
	let showNewDialog = $state(page.url.searchParams.has(NEW_PARAM));
	let isCreating = $state(false);
	let showImportDialog = $state(false);
	let isImporting = $state(false);
	let showLaunch = $state(false);
	let launchEngineId = $state('');
	let query = $state('');
	let sortKey = $state<SortKey>('recent');

	$effect(() => {
		untrack(() => engineCatalogStore.fetch());
	});

	$effect(() => {
		if (page.url.searchParams.has(NEW_PARAM)) untrack(() => (showNewDialog = true));
	});

	$effect(() => {
		if (showNewDialog) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (!params.has(NEW_PARAM)) return;
		params.delete(NEW_PARAM);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {}
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (scanEnginesStore.fetchedProjectId !== project.id) {
					selectedIds.clear();
					scanEnginesStore.fetchEngines(project.id);
				}
			});
		}
	});

	const stages = $derived(engineCatalogStore.stages);

	function lastUsed(engine: ScanEngine): number {
		return engine.last_used_at ? Date.parse(engine.last_used_at) : 0;
	}

	function compare(a: ScanEngine, b: ScanEngine): number {
		if (sortKey === 'name') return a.name.localeCompare(b.name);
		if (sortKey === 'usage') {
			return (b.usage?.scans ?? 0) - (a.usage?.scans ?? 0) || a.name.localeCompare(b.name);
		}
		return (
			lastUsed(b) - lastUsed(a) ||
			Date.parse(b.updated_at) - Date.parse(a.updated_at) ||
			a.name.localeCompare(b.name)
		);
	}

	const visibleEngines = $derived.by(() => {
		const term = query.trim().toLowerCase();
		const list = scanEnginesStore.engines.filter((engine) => {
			if (!term) return true;
			if (engine.name.toLowerCase().includes(term)) return true;
			if ((engine.description ?? '').toLowerCase().includes(term)) return true;
			if (engine.intensity.includes(term)) return true;
			return summarize(engine.stages ?? {}, stages, engine.intensity).tools.some((t) =>
				t.includes(term)
			);
		});
		return list.sort(compare);
	});

	async function handleCreate(name: string, preset: EnginePreset) {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}
		isCreating = true;
		try {
			const created = await scanEnginesStore.createEngine(project.id, {
				name,
				description: preset.description,
				intensity: preset.intensity,
				stages: preset.stages
			});
			if (created) {
				showNewDialog = false;
				toast.success('Engine created');
				goto(ROUTES.engine(created.id));
			} else {
				toast.error(scanEnginesStore.error ?? 'Engine not created');
			}
		} finally {
			isCreating = false;
		}
	}

	async function handleImport(yaml: string) {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}
		isImporting = true;
		try {
			const imported = await scanEnginesStore.importYaml(project.id, yaml);
			if (imported) {
				showImportDialog = false;
				toast.success('Engine imported');
				goto(ROUTES.engine(imported.id));
			} else {
				toast.error(scanEnginesStore.error ?? 'Engine not imported');
			}
		} finally {
			isImporting = false;
		}
	}

	async function handleDuplicate(engine: ScanEngine) {
		const project = projectsStore.activeProject;
		if (!project) return;
		const copy = await scanEnginesStore.duplicateEngine(engine.id, project.id);
		if (copy) toast.success('Engine duplicated');
		else toast.error(scanEnginesStore.error ?? 'Engine not duplicated');
	}

	async function handleExport(engine: ScanEngine) {
		const project = projectsStore.activeProject;
		if (!project) return;
		const yaml = await scanEnginesStore.exportYaml(engine.id, project.id);
		if (yaml) {
			downloadBlob(`${engine.name}.yaml`, yaml, 'text/yaml');
			toast.success('YAML exported');
		} else {
			toast.error(scanEnginesStore.error ?? 'Engine not exported');
		}
	}

	function toggleSelect(id: string) {
		if (selectedIds.has(id)) selectedIds.delete(id);
		else selectedIds.add(id);
	}

	function clearSelection() {
		selectedIds.clear();
	}

	function toggleSelectAll() {
		const all = scanEnginesStore.engines.filter((e) => !e.builtin);
		if (selectedIds.size >= all.length) selectedIds.clear();
		else for (const e of all) selectedIds.add(e.id);
	}

	async function confirmDelete() {
		if (!engineToDelete) return;
		isDeleting = true;
		try {
			const ok = await scanEnginesStore.deleteEngine(engineToDelete.id);
			if (ok) {
				toast.success('Engine deleted');
				selectedIds.delete(engineToDelete.id);
				showDeleteDialog = false;
				engineToDelete = null;
			} else {
				toast.error(scanEnginesStore.error ?? 'Engine not deleted');
			}
		} finally {
			isDeleting = false;
		}
	}

	async function handleRefresh() {
		const project = projectsStore.activeProject;
		if (!project) return;
		isRefreshing = true;
		try {
			await Promise.all([
				scanEnginesStore.fetchEngines(project.id),
				engineCatalogStore.fetch(true)
			]);
			if (scanEnginesStore.error) toast.error(scanEnginesStore.error);
		} finally {
			isRefreshing = false;
		}
	}

	const stageCount = $derived(stages.length);
	const total = $derived(scanEnginesStore.engines.length);
	const selectable = $derived(scanEnginesStore.engines.filter((e) => !e.builtin).length);
	const loaded = $derived(
		Boolean(projectsStore.activeProject) &&
			scanEnginesStore.fetchedProjectId === projectsStore.activeProject?.id
	);
	const loadFailed = $derived(
		!loaded && Boolean(scanEnginesStore.error) && !scanEnginesStore.isLoading
	);
</script>

<svelte:head><title>{pageTitle(routeLabels.engines)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="min-w-0">
			<h1 class="text-2xl font-semibold tracking-tight">Scan engines</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				Stage selection and settings for a scan{stageCount
					? ` · ${stageCount} stages available`
					: ''}
			</p>
		</div>
		<div class="flex flex-wrap items-center gap-2">
			<Hint text="Refresh">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon-sm"
						aria-label="Refresh"
						onclick={handleRefresh}
						disabled={isRefreshing}
					>
						<RefreshCw class="size-4 {isRefreshing ? 'animate-spin' : ''}" />
					</Button>
				{/snippet}
			</Hint>
			<Button variant="outline" size="sm" onclick={() => (showImportDialog = true)}>
				<Upload class="size-4" />
				Import
			</Button>
			<Button size="sm" onclick={() => (showNewDialog = true)}>
				<Plus class="size-4" />
				New engine
			</Button>
		</div>
	</div>

	{#if loadFailed}
		<EmptyState
			icon={TriangleAlert}
			title="Scan engines not loaded"
			description={scanEnginesStore.error ?? undefined}
		>
			<Button variant="outline" size="sm" onclick={handleRefresh}>Retry</Button>
		</EmptyState>
	{:else if !loaded}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div class="flex flex-col gap-3 rounded-xl border border-border p-4">
					<Skeleton class="h-[18px] w-40" />
					<Skeleton class="h-3.5 w-4/5" />
					<Skeleton class="mt-2 h-[22px] w-[200px]" />
					<Skeleton class="h-3.5 w-[140px]" />
					<Skeleton class="mt-3 h-6 w-full" />
				</div>
			{/each}
		</div>
	{:else if total > 0}
		<div class="flex flex-wrap items-center gap-2">
			<InputGroup.Root class="h-9 w-full sm:max-w-xs">
				<InputGroup.Addon>
					<Search />
				</InputGroup.Addon>
				<InputGroup.Input bind:value={query} placeholder="Search engines, tools…" />
			</InputGroup.Root>
			<Select.Root
				type="single"
				value={sortKey}
				onValueChange={(v) => v && (sortKey = v as SortKey)}
			>
				<Select.Trigger class="h-9 w-[170px] gap-2 text-sm" aria-label="Sort engines">
					<ArrowUpDown size={14} class="text-muted-foreground" />
					{SORT_LABELS[sortKey]}
				</Select.Trigger>
				<Select.Content>
					{#each Object.entries(SORT_LABELS) as [key, label] (key)}
						<Select.Item value={key} {label}>{label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<span class="ml-auto text-xs text-muted-foreground tabular-nums">
				{#if query.trim()}
					{visibleEngines.length} of {total} engine{total === 1 ? '' : 's'}
				{:else}
					{total} engine{total === 1 ? '' : 's'}
				{/if}
			</span>
		</div>

		{#if visibleEngines.length === 0}
			<EmptyState icon={SearchX} title="No engines match" compact>
				<Button variant="outline" size="sm" onclick={() => (query = '')}>Clear search</Button>
			</EmptyState>
		{:else}
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
				{#each visibleEngines as engine (engine.id)}
					<EngineListCard
						{engine}
						{stages}
						isSelected={selectedIds.has(engine.id)}
						onSelect={() => toggleSelect(engine.id)}
						onEdit={() => goto(ROUTES.engine(engine.id))}
						onRun={() => {
							launchEngineId = engine.id;
							showLaunch = true;
						}}
						onDuplicate={() => handleDuplicate(engine)}
						onExport={() => handleExport(engine)}
						onDelete={() => {
							engineToDelete = engine;
							showDeleteDialog = true;
						}}
					/>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<ImportEngineDialog
	open={showImportDialog}
	catalog={engineCatalogStore.catalog}
	{isImporting}
	onOpenChange={(o) => (showImportDialog = o)}
	onImport={handleImport}
/>

<LaunchDialog bind:open={showLaunch} presetEngineId={launchEngineId} />

<NewEngineDialog
	open={showNewDialog}
	presets={engineCatalogStore.presets}
	{stages}
	{isCreating}
	onOpenChange={(o) => (showNewDialog = o)}
	onCreate={handleCreate}
/>

<SelectionDeleteBar
	ids={[...selectedIds]}
	noun="engine"
	remove={(id) => scanEnginesApi.delete(id, projectsStore.activeProject?.id ?? '')}
	onDone={() => {
		selectedIds.clear();
		const project = projectsStore.activeProject;
		if (project) void scanEnginesStore.fetchEngines(project.id);
	}}
	onClear={clearSelection}
>
	<Button variant="ghost" size="sm" class="font-medium" onclick={toggleSelectAll}>
		<ListChecks class="h-3.5 w-3.5 text-muted-foreground" />
		{selectedIds.size >= selectable ? 'Deselect all' : 'Select all'}
	</Button>
</SelectionDeleteBar>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title="Delete engine"
	description={`Engine ${engineToDelete?.name ?? ''} is removed.`}
	{isDeleting}
	onOpenChange={(open) => {
		showDeleteDialog = open;
		if (!open) engineToDelete = null;
	}}
	onConfirm={confirmDelete}
/>
