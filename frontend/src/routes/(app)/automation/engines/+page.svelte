<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import Upload from '@lucide/svelte/icons/upload';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import AlertCircle from '@lucide/svelte/icons/alert-circle';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ListChecks from '@lucide/svelte/icons/list-checks';
	import Search from '@lucide/svelte/icons/search';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import SearchX from '@lucide/svelte/icons/search-x';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Alert from '$lib/components/ui/alert';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as Select from '$lib/components/ui/select';
	import EmptyState from '@/components/empty-state.svelte';
	import EngineListCard from '$lib/components/engines/engine-list-card.svelte';
	import StageList from '$lib/components/engines/stage-list.svelte';
	import FootprintMeter from '$lib/components/engines/footprint-meter.svelte';
	import NewEngineDialog from '$lib/components/engines/new-engine-dialog.svelte';
	import ImportEngineDialog from '$lib/components/engines/import-engine-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import SelectionActionBar from '@/components/selection-action-bar.svelte';
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
	let deleteMode = $state<'single' | 'bulk'>('single');
	const selectedIds = new SvelteSet<string>();
	let showNewDialog = $state(false);
	let initialPreset = $state<string | null>(null);
	let isCreating = $state(false);
	let showImportDialog = $state(false);
	let isImporting = $state(false);
	let showLaunch = $state(false);
	let launchEngineId = $state('');
	let query = $state('');
	let sortKey = $state<SortKey>('recent');

	$effect(() => {
		engineCatalogStore.fetch();
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

	function openNew(preset: string | null = null) {
		initialPreset = preset;
		showNewDialog = true;
	}

	async function handleCreate(name: string, preset: EnginePreset) {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project selected');
			return;
		}
		isCreating = true;
		try {
			const created = await scanEnginesStore.createEngine(project.id, {
				name,
				description: preset.description,
				stages: preset.stages
			});
			if (created) {
				showNewDialog = false;
				toast.success(`Created "${created.name}"`);
				goto(ROUTES.engine(created.id));
			} else {
				toast.error(scanEnginesStore.error ?? 'Engine could not be created');
			}
		} finally {
			isCreating = false;
		}
	}

	async function handleImport(yaml: string) {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project selected');
			return;
		}
		isImporting = true;
		try {
			const imported = await scanEnginesStore.importYaml(project.id, yaml);
			if (imported) {
				showImportDialog = false;
				toast.success(`Imported "${imported.name}"`);
				goto(ROUTES.engine(imported.id));
			} else {
				toast.error(scanEnginesStore.error ?? 'Engine could not be imported');
			}
		} finally {
			isImporting = false;
		}
	}

	async function handleDuplicate(engine: ScanEngine) {
		const project = projectsStore.activeProject;
		if (!project) return;
		const copy = await scanEnginesStore.duplicateEngine(engine.id, project.id);
		if (copy) toast.success(`Duplicated "${engine.name}"`);
		else toast.error(scanEnginesStore.error ?? 'Engine could not be duplicated');
	}

	async function handleExport(engine: ScanEngine) {
		const project = projectsStore.activeProject;
		if (!project) return;
		const yaml = await scanEnginesStore.exportYaml(engine.id, project.id);
		if (yaml) {
			downloadBlob(`${engine.name}.yaml`, yaml, 'text/yaml');
			toast.success('YAML exported');
		} else {
			toast.error(scanEnginesStore.error ?? 'Engine could not be exported');
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
		const all = scanEnginesStore.engines;
		if (selectedIds.size >= all.length) selectedIds.clear();
		else for (const e of all) selectedIds.add(e.id);
	}

	function requestBulkDelete() {
		if (selectedIds.size === 0) return;
		deleteMode = 'bulk';
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		isDeleting = true;
		try {
			if (deleteMode === 'single') {
				if (!engineToDelete) return;
				const ok = await scanEnginesStore.deleteEngine(engineToDelete.id);
				if (ok) {
					toast.success(`Deleted "${engineToDelete.name}"`);
					selectedIds.delete(engineToDelete.id);
					showDeleteDialog = false;
					engineToDelete = null;
				} else {
					toast.error(scanEnginesStore.error ?? 'Engine could not be deleted');
				}
				return;
			}

			const ids = Array.from(selectedIds);
			let failed = 0;
			let lastError = '';
			for (const id of ids) {
				const ok = await scanEnginesStore.deleteEngine(id);
				if (ok) selectedIds.delete(id);
				else {
					failed++;
					lastError = scanEnginesStore.error ?? '';
				}
			}
			const deleted = ids.length - failed;
			if (deleted) toast.success(`${deleted} engine${deleted !== 1 ? 's' : ''} deleted`);
			if (failed) {
				toast.error(
					`${failed} engine${failed !== 1 ? 's' : ''} kept${lastError ? `. ${lastError}` : ''}`
				);
			}
			showDeleteDialog = false;
		} finally {
			isDeleting = false;
		}
	}

	const deleteTitle = $derived(
		deleteMode === 'single'
			? 'Delete this engine?'
			: `Delete ${selectedIds.size} engine${selectedIds.size !== 1 ? 's' : ''}?`
	);
	const deleteDescription = $derived(
		deleteMode === 'single'
			? 'Removes this engine from the project. Completed scans and their results are unaffected.'
			: 'Removes the selected engines from the project. Engines referenced by a schedule or a running scan are skipped. Completed scans and their results are unaffected.'
	);

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
			else toast.success('Engines refreshed');
		} finally {
			isRefreshing = false;
		}
	}

	const stageCount = $derived(stages.length);
	const total = $derived(scanEnginesStore.engines.length);
</script>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div class="max-w-2xl">
			<h1 class="text-2xl font-semibold tracking-tight">Scan engines</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				An engine defines which stages run against a target and how each is tuned. {#if stageCount}{stageCount}
					stages are available on this instance.{/if}
			</p>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9"
				aria-label="Refresh"
				onclick={handleRefresh}
				disabled={isRefreshing}
			>
				<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
			</Button>
			<Button variant="outline" class="gap-2" onclick={() => (showImportDialog = true)}>
				<Upload class="h-4 w-4" />
				Import
			</Button>
			<Button class="gap-2" onclick={() => openNew()}>
				<Plus class="h-4 w-4" />
				New engine
			</Button>
		</div>
	</div>

	{#if scanEnginesStore.error && !scanEnginesStore.isLoading}
		<Alert.Root variant="destructive">
			<AlertCircle />
			<Alert.Title>Scan engines could not be loaded</Alert.Title>
			<Alert.Description class="flex flex-wrap items-center justify-between gap-3">
				<span>{scanEnginesStore.error}</span>
				<Button
					variant="outline"
					size="sm"
					class="gap-1.5"
					onclick={handleRefresh}
					disabled={isRefreshing}
				>
					<RefreshCw class="h-3.5 w-3.5 {isRefreshing ? 'animate-spin' : ''}" />
					Retry
				</Button>
			</Alert.Description>
		</Alert.Root>
	{/if}

	{#if scanEnginesStore.isLoading}
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
	{:else if total === 0}
		<section class="rounded-xl border border-border bg-muted/20 p-6 sm:p-8">
			<div class="max-w-xl">
				<h2 class="text-lg font-semibold tracking-tight">No scan engines</h2>
				<p class="mt-1 text-sm text-muted-foreground">
					An engine defines which stages run against a target and how each is tuned. Start from a
					preset, or configure one field by field.
				</p>
			</div>
			{#if engineCatalogStore.presets.length}
				<div class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
					{#each engineCatalogStore.presets as preset (preset.name)}
						{@const summary = summarize(preset.stages, stages, 'normal')}
						<button
							type="button"
							class="group flex flex-col gap-3 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-foreground/25 hover:bg-card focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							onclick={() => openNew(preset.name)}
						>
							<span class="flex items-start justify-between gap-2">
								<span class="text-sm font-medium">{preset.title}</span>
								<ArrowRight
									size={14}
									class="mt-0.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
								/>
							</span>
							<span class="text-xs text-muted-foreground">{preset.description}</span>
							<StageList {stages} config={preset.stages} variant="inline" max={4} class="mt-auto" />
							<span class="flex items-center justify-between gap-2 text-[11px]">
								<span class="text-muted-foreground tabular-nums">
									{summary.activeStages} of {summary.totalStages} stages
								</span>
								<FootprintMeter
									footprint={summary.footprint}
									requestsPerSecond={summary.requestsPerSecond}
									class="text-[11px]"
								/>
							</span>
						</button>
					{/each}
				</div>
			{/if}
			<p class="mt-5 text-xs text-muted-foreground">
				Already have one?
				<button
					type="button"
					class="font-medium text-foreground underline-offset-4 hover:underline"
					onclick={() => (showImportDialog = true)}
				>
					Import a YAML file
				</button>
			</p>
		</section>
	{:else}
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
			<EmptyState
				icon={SearchX}
				title="No engines match"
				description="Widen the search or remove a filter."
				compact
			>
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
							deleteMode = 'single';
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
	{initialPreset}
	onOpenChange={(o) => (showNewDialog = o)}
	onCreate={handleCreate}
/>

<SelectionActionBar selectedCount={selectedIds.size} noun="engine" onClear={clearSelection}>
	<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={toggleSelectAll}>
		<ListChecks class="h-3.5 w-3.5 text-muted-foreground" />
		{selectedIds.size >= total ? 'Deselect all' : 'Select all'}
	</Button>
	<Button
		variant="ghost"
		size="sm"
		class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
		onclick={requestBulkDelete}
	>
		<Trash2 class="h-3.5 w-3.5" />
		Delete
	</Button>
</SelectionActionBar>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title={deleteTitle}
	description={deleteDescription}
	{isDeleting}
	onOpenChange={(open) => {
		showDeleteDialog = open;
		if (!open) engineToDelete = null;
	}}
	onConfirm={confirmDelete}
/>
