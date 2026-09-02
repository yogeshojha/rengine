<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import Upload from '@lucide/svelte/icons/upload';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Network from '@lucide/svelte/icons/network';
	import AlertCircle from '@lucide/svelte/icons/alert-circle';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ListChecks from '@lucide/svelte/icons/list-checks';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Alert from '$lib/components/ui/alert';
	import EmptyState from '@/components/empty-state.svelte';
	import EngineListCard from '$lib/components/engines/engine-list-card.svelte';
	import NewEngineDialog from '$lib/components/engines/new-engine-dialog.svelte';
	import ImportEngineDialog from '$lib/components/engines/import-engine-dialog.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import SelectionActionBar from '@/components/selection-action-bar.svelte';
	import type { EnginePreset, ScanEngine } from '$lib/types/scan-engine';

	let isRefreshing = $state(false);
	let engineToDelete = $state<ScanEngine | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let deleteMode = $state<'single' | 'bulk'>('single');
	const selectedIds = new SvelteSet<string>();
	let showNewDialog = $state(false);
	let isCreating = $state(false);
	let showImportDialog = $state(false);
	let isImporting = $state(false);
	let showLaunch = $state(false);
	let launchEngineId = $state('');

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
				toast.error(scanEnginesStore.error ?? 'Failed to create engine');
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
				toast.error(scanEnginesStore.error ?? 'Failed to import engine');
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
		else toast.error(scanEnginesStore.error ?? 'Failed to duplicate engine');
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
					toast.error(scanEnginesStore.error ?? 'Failed to delete engine');
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
					`${failed} engine${failed !== 1 ? 's' : ''} kept${lastError ? ` — ${lastError}` : ''}`
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
			? 'Scans already run with it keep their results. This is permanent.'
			: `Scans already run with ${selectedIds.size === 1 ? 'it' : 'them'} keep their results. An engine still used by a schedule or a running scan is kept. This is permanent.`
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

	const stageCount = $derived(engineCatalogStore.stages.length);
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">Scan Engines</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				Reusable scan configurations built from the
				{stageCount || ''}
				stages installed on this instance.
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
			<Button class="gap-2" onclick={() => (showNewDialog = true)}>
				<Plus class="h-4 w-4" />
				New engine
			</Button>
		</div>
	</div>

	{#if scanEnginesStore.error && !scanEnginesStore.isLoading}
		<Alert.Root variant="destructive">
			<AlertCircle />
			<Alert.Title>Couldn't load scan engines</Alert.Title>
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
				<div class="flex flex-col gap-3 rounded-xl border border-border p-[16px_18px]">
					<Skeleton class="h-[18px] w-40" />
					<Skeleton class="h-3.5 w-4/5" />
					<Skeleton class="h-[22px] w-[180px]" />
					<Skeleton class="h-3.5 w-[120px]" />
				</div>
			{/each}
		</div>
	{:else if scanEnginesStore.engines.length === 0}
		<EmptyState
			icon={Network}
			title="No scan engines yet"
			description="An engine decides which stages run and how they're tuned. Start from a preset and adjust."
		>
			<Button class="gap-2" onclick={() => (showNewDialog = true)}>
				<Plus size={15} />
				Create your first engine
			</Button>
		</EmptyState>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each scanEnginesStore.engines as engine (engine.id)}
				<EngineListCard
					{engine}
					stages={engineCatalogStore.stages}
					isSelected={selectedIds.has(engine.id)}
					onSelect={() => toggleSelect(engine.id)}
					onEdit={() => goto(ROUTES.engine(engine.id))}
					onRun={() => {
						launchEngineId = engine.id;
						showLaunch = true;
					}}
					onDuplicate={() => handleDuplicate(engine)}
					onDelete={() => {
						deleteMode = 'single';
						engineToDelete = engine;
						showDeleteDialog = true;
					}}
				/>
			{/each}
		</div>
	{/if}
</div>

<ImportEngineDialog
	open={showImportDialog}
	catalog={engineCatalogStore.catalog}
	{isImporting}
	onOpenChange={(o) => (showImportDialog = o)}
	onImport={handleImport}
/>

<LaunchModal bind:open={showLaunch} presetEngineId={launchEngineId} />

<NewEngineDialog
	open={showNewDialog}
	presets={engineCatalogStore.presets}
	{isCreating}
	onOpenChange={(o) => (showNewDialog = o)}
	onCreate={handleCreate}
/>

<SelectionActionBar selectedCount={selectedIds.size} noun="engine" onClear={clearSelection}>
	<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={toggleSelectAll}>
		<ListChecks class="h-3.5 w-3.5 text-muted-foreground" />
		{selectedIds.size >= scanEnginesStore.engines.length ? 'Deselect all' : 'Select all'}
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
