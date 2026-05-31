<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { Plus, RefreshCw, KeyRound } from 'lucide-svelte';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Button } from '$lib/components/ui/button';
	import ContextListCard from '$lib/components/contexts/context-list-card.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import type { ScanContextRead } from '$lib/types/scan-context';

	let isRefreshing = $state(false);
	let contextToDelete = $state<ScanContextRead | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (!scanContextsStore.hasFetched) {
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
		goto(`/automation/contexts/new?project=${project.id}`);
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
		contextToDelete = context;
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		if (!contextToDelete?.id) return;
		isDeleting = true;
		try {
			const ok = await scanContextsStore.deleteContext(
				contextToDelete.id,
				contextToDelete.project_id
			);
			if (ok) {
				toast.success(`Deleted "${contextToDelete.name}"`);
				showDeleteDialog = false;
				contextToDelete = null;
			} else {
				toast.error(scanContextsStore.error ?? 'Failed to delete context');
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
	<!-- Page header -->
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
				New Context
			</Button>
		</div>
	</div>

	{#if scanContextsStore.error && !scanContextsStore.isLoading}
		<div class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
			{scanContextsStore.error}
		</div>
	{/if}

	{#if scanContextsStore.isLoading}
		<!-- Loading skeleton -->
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div class="h-[150px] animate-pulse rounded-[10px] border border-border bg-muted/40"></div>
			{/each}
		</div>
	{:else if scanContextsStore.contexts.length === 0}
		<!-- Empty state -->
		<div
			class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-muted/20 px-6 py-20 text-center"
		>
			<div class="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
				<KeyRound size={28} class="text-muted-foreground" />
			</div>
			<h2 class="mb-2 text-lg font-bold text-foreground">No scan contexts yet</h2>
			<p class="mb-6 max-w-md text-sm leading-relaxed text-muted-foreground">
				Contexts hold authentication, rate limits, and scope rules you can reuse across scans.
				Scans can also run with Context: None.
			</p>
			<Button onclick={handleNewContext} class="gap-2">
				<Plus size={15} />
				Create Your First Context
			</Button>
		</div>
	{:else}
		<!-- Context grid -->
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each scanContextsStore.contexts as context (context.id)}
				<ContextListCard
					{context}
					onEdit={() => goto(`/automation/contexts/${context.id}`)}
					onDuplicate={() => handleDuplicate(context)}
					onDelete={() => handleDeleteRequest(context)}
				/>
			{/each}
		</div>

		<p class="pt-2 text-center text-xs text-muted-foreground">
			{scanContextsStore.contexts.length} context{scanContextsStore.contexts.length !== 1 ? 's' : ''} in
			this project
		</p>
	{/if}
</div>

{#if contextToDelete}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete Context"
		description="Are you sure you want to delete '{contextToDelete.name}'? This action cannot be undone."
		{isDeleting}
		onOpenChange={(open) => {
			showDeleteDialog = open;
			if (!open) contextToDelete = null;
		}}
		onConfirm={confirmDelete}
	/>
{/if}
