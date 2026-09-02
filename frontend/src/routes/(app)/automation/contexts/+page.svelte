<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ListChecks from '@lucide/svelte/icons/list-checks';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '@/components/empty-state.svelte';
	import ContextListCard from '$lib/components/contexts/context-list-card.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import SelectionActionBar from '@/components/selection-action-bar.svelte';
	import type { ScanContextRead } from '$lib/types/scan-context';

	let isRefreshing = $state(false);
	let showLaunch = $state(false);
	let launchContextId = $state('');
	let contextToDelete = $state<ScanContextRead | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let deleteMode = $state<'single' | 'bulk'>('single');
	const selectedIds = new SvelteSet<string>();

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (scanContextsStore.fetchedProjectId !== project.id) {
					selectedIds.clear();
					scanContextsStore.fetchContexts(project.id);
				}
			});
		}
	});

	function handleNewContext() {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project selected');
			return;
		}
		goto(ROUTES.newContext(project.id));
	}

	async function handleDuplicate(context: ScanContextRead) {
		const project = projectsStore.activeProject;
		if (!project || !context.id) return;
		try {
			const dup = await scanContextsStore.duplicateContext(context.id, project.id);
			if (dup) {
				toast.success(`Duplicated "${context.name}"`);
			} else {
				toast.error(scanContextsStore.error ?? 'Failed to duplicate context');
			}
		} catch {
			toast.error('Failed to duplicate context');
		}
	}

	function handleDeleteRequest(context: ScanContextRead) {
		deleteMode = 'single';
		contextToDelete = context;
		showDeleteDialog = true;
	}

	function toggleSelect(id: string) {
		if (selectedIds.has(id)) selectedIds.delete(id);
		else selectedIds.add(id);
	}

	function clearSelection() {
		selectedIds.clear();
	}

	function toggleSelectAll() {
		const all = scanContextsStore.contexts;
		if (selectedIds.size >= all.length) selectedIds.clear();
		else for (const c of all) selectedIds.add(c.id);
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
				if (!contextToDelete?.id) return;
				const ok = await scanContextsStore.deleteContext(
					contextToDelete.id,
					contextToDelete.project_id
				);
				if (ok) {
					toast.success(`Deleted "${contextToDelete.name}"`);
					selectedIds.delete(contextToDelete.id);
					showDeleteDialog = false;
					contextToDelete = null;
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to delete context');
				}
				return;
			}

			const byId = new Map(scanContextsStore.contexts.map((c) => [c.id, c]));
			const ids = Array.from(selectedIds);
			let failed = 0;
			let lastError = '';
			for (const id of ids) {
				const ok = await scanContextsStore.deleteContext(id, byId.get(id)?.project_id);
				if (ok) selectedIds.delete(id);
				else {
					failed++;
					lastError = scanContextsStore.error ?? '';
				}
			}
			const deleted = ids.length - failed;
			if (deleted) toast.success(`${deleted} context${deleted !== 1 ? 's' : ''} deleted`);
			if (failed) {
				toast.error(
					`${failed} context${failed !== 1 ? 's' : ''} kept${lastError ? ` — ${lastError}` : ''}`
				);
			}
			showDeleteDialog = false;
		} finally {
			isDeleting = false;
		}
	}

	const deleteTitle = $derived(
		deleteMode === 'single'
			? 'Delete this context?'
			: `Delete ${selectedIds.size} context${selectedIds.size !== 1 ? 's' : ''}?`
	);
	const deleteDescription = $derived(
		deleteMode === 'single'
			? 'Scans already run with it keep their results. This is permanent.'
			: `Scans already run with ${selectedIds.size === 1 ? 'it' : 'them'} keep their results. A context still used by a schedule or a running scan is kept. This is permanent.`
	);

	async function handleRefresh() {
		const project = projectsStore.activeProject;
		if (!project) return;
		isRefreshing = true;
		try {
			await scanContextsStore.fetchContexts(project.id);
			if (scanContextsStore.error) {
				toast.error(scanContextsStore.error);
			} else {
				toast.success('Refreshed');
			}
		} finally {
			isRefreshing = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">Scan Contexts</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				Reusable auth, rate limits, and scope overrides layered onto an engine at scan time
			</p>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9"
				onclick={handleRefresh}
				disabled={isRefreshing}
			>
				<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
			</Button>
			<Button onclick={handleNewContext} class="gap-2">
				<Plus class="h-4 w-4" />
				New context
			</Button>
		</div>
	</div>

	{#if scanContextsStore.error && !scanContextsStore.isLoading}
		<div
			class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
		>
			{scanContextsStore.error}
		</div>
	{/if}

	{#if scanContextsStore.isLoading}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<Skeleton class="h-[150px] rounded-lg" />
			{/each}
		</div>
	{:else if scanContextsStore.contexts.length === 0}
		<EmptyState
			icon={KeyRound}
			title="No scan contexts yet"
			description="Contexts hold authentication, rate limits, and scope rules you can reuse across scans. Scans can also run with Context: None."
		>
			<Button onclick={handleNewContext} class="gap-2">
				<Plus size={15} />
				Create a context
			</Button>
		</EmptyState>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each scanContextsStore.contexts as context (context.id)}
				<ContextListCard
					{context}
					isSelected={selectedIds.has(context.id)}
					onSelect={() => toggleSelect(context.id)}
					onEdit={() => goto(ROUTES.context(context.id))}
					onRun={() => {
						launchContextId = context.id;
						showLaunch = true;
					}}
					onDuplicate={() => handleDuplicate(context)}
					onDelete={() => handleDeleteRequest(context)}
				/>
			{/each}
		</div>

		<p class="pt-2 text-center text-xs text-muted-foreground">
			{scanContextsStore.contexts.length} context{scanContextsStore.contexts.length !== 1
				? 's'
				: ''} in this project
		</p>
	{/if}
</div>

<SelectionActionBar selectedCount={selectedIds.size} noun="context" onClear={clearSelection}>
	<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={toggleSelectAll}>
		<ListChecks class="h-3.5 w-3.5 text-muted-foreground" />
		{selectedIds.size >= scanContextsStore.contexts.length ? 'Deselect all' : 'Select all'}
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
		if (!open) contextToDelete = null;
	}}
	onConfirm={confirmDelete}
/>

<LaunchModal bind:open={showLaunch} presetContextId={launchContextId} />
