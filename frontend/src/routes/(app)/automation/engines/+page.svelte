<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { Plus, RefreshCw, Network, Zap, AlertCircle } from 'lucide-svelte';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Alert from '$lib/components/ui/alert';
	import * as Empty from '$lib/components/ui/empty';
	import EngineListCard from '$lib/components/engines/engine-list-card.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';

	let isRefreshing = $state(false);
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let engineToDelete = $state<any | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (!scanEnginesStore.hasFetched) {
					scanEnginesStore.fetchEngines(project.id);
				}
			});
		}
	});

	function handleNewEngine() {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project selected');
			return;
		}
		goto(`/automation/engines/new?project=${project.id}`);
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	async function handleDuplicate(engine: any) {
		const project = projectsStore.activeProject;
		if (!project || !engine.id) return;

		try {
			const duplicate = await scanEnginesStore.duplicateEngine(engine.id, project.id);
			if (duplicate) {
				toast.success(`Duplicated "${engine.name}"`);
			} else {
				toast.error(scanEnginesStore.error ?? 'Failed to duplicate engine');
			}
		} catch {
			toast.error('Failed to duplicate engine');
		}
	}

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	function handleDeleteRequest(engine: any) {
		engineToDelete = engine;
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		if (!engineToDelete?.id) return;
		isDeleting = true;
		try {
			const ok = await scanEnginesStore.deleteEngine(engineToDelete.id);
			if (ok) {
				toast.success(`Deleted "${engineToDelete.name}"`);
				showDeleteDialog = false;
				engineToDelete = null;
			} else {
				toast.error(scanEnginesStore.error ?? 'Failed to delete engine');
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
			await scanEnginesStore.fetchEngines(project.id);
			if (scanEnginesStore.error) {
				toast.error(scanEnginesStore.error);
			} else {
				toast.success('Engines refreshed');
			}
		} finally {
			isRefreshing = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">Scan Engines</h1>
			<p class="text-sm text-muted-foreground mt-1">
				Build and manage reusable scan configurations for your recon pipeline
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
			<Button onclick={handleNewEngine} class="gap-2">
				<Plus class="h-4 w-4" />
				New Engine
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
				<div class="h-[188px] overflow-hidden rounded-[14px] border border-border">
					<Skeleton class="h-1 rounded-none" />
					<div class="flex flex-col gap-3 p-[18px_20px]">
						<div class="flex items-center gap-2.5">
							<Skeleton class="h-[18px] w-40" />
							<Skeleton class="h-[18px] w-[60px] rounded-full" />
						</div>
						<Skeleton class="h-3.5 w-4/5" />
						<div class="flex gap-1.5">
							<Skeleton class="h-[26px] w-[90px]" />
							<Skeleton class="h-[26px] w-[90px]" />
							<Skeleton class="h-[26px] w-20" />
						</div>
						<div class="flex justify-between pt-1">
							<Skeleton class="h-3.5 w-[100px]" />
							<Skeleton class="h-7 w-[60px]" />
						</div>
					</div>
				</div>
			{/each}
		</div>

	{:else if scanEnginesStore.engines.length === 0}
		<Empty.Root class="border bg-muted/20 py-20">
			<Empty.Header>
				<Empty.Media class="size-16 rounded-2xl bg-muted">
					<Network size={28} class="text-muted-foreground" />
				</Empty.Media>
				<Empty.Title class="text-lg font-bold">No scan engines yet</Empty.Title>
				<Empty.Description class="max-w-md">
					Scan engines define which tools run, in which order, and with what configuration. Create
					your first engine to get started.
				</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<div class="flex flex-wrap items-center justify-center gap-2.5">
					<Button onclick={handleNewEngine} class="gap-2">
						<Plus size={15} />
						Create Your First Engine
					</Button>
					<Badge variant="secondary" class="gap-1.5 text-muted-foreground">
						<Zap size={12} />
						3 recon phases: Discovery &rarr; Expansion &rarr; Depth
					</Badge>
				</div>
			</Empty.Content>
		</Empty.Root>

	{:else}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each scanEnginesStore.engines as engine (engine.id)}
				{@const cardEngine = engine as unknown as import('$lib/types/engine').ScanEngine}
				<EngineListCard
					engine={cardEngine}
					onEdit={() => goto(`/automation/engines/${engine.id}`)}
					onDuplicate={() => handleDuplicate(engine)}
					onDelete={() => handleDeleteRequest(engine)}
				/>
			{/each}
		</div>

		<p class="text-xs text-muted-foreground text-center pt-2">
			{scanEnginesStore.engines.length} engine{scanEnginesStore.engines.length !== 1 ? 's' : ''} in this project
		</p>
	{/if}
</div>

{#if engineToDelete}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete Engine"
		description="Are you sure you want to delete '{engineToDelete.name}'? This action cannot be undone."
		{isDeleting}
		onOpenChange={(open) => {
			showDeleteDialog = open;
			if (!open) engineToDelete = null;
		}}
		onConfirm={confirmDelete}
	/>
{/if}
