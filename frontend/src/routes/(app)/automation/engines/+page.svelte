<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { Plus, RefreshCw, Network, Zap } from 'lucide-svelte';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Button } from '$lib/components/ui/button';
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
		// Navigate to the "new" editor — no API call yet. The engine is only
		// persisted when the user explicitly clicks Save Engine.
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
		} finally {
			isRefreshing = false;
			toast.success('Refreshed');
		}
	}
</script>

<div class="space-y-6">
	<!-- Page header -->
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

	<!-- Error banner -->
	{#if scanEnginesStore.error && !scanEnginesStore.isLoading}
		<div
			style="
				padding: 12px 16px;
				border-radius: 10px;
				border: 1px solid #fca5a5;
				background: #fef2f2;
				color: #991b1b;
				font-size: 14px;
			"
		>
			{scanEnginesStore.error}
		</div>
	{/if}

	<!-- Content area -->
	{#if scanEnginesStore.isLoading}
		<!-- Loading skeleton -->
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div
					style="
						border-radius: 14px;
						border: 1.5px solid #e2e8f0;
						background: white;
						overflow: hidden;
						height: 188px;
					"
					class="skeleton-card"
				>
					<div style="height: 4px; background: #f1f5f9;"></div>
					<div style="padding: 18px 20px; display: flex; flex-direction: column; gap: 12px;">
						<div style="display: flex; gap: 10px; align-items: center;">
							<div class="skel" style="height: 18px; width: 160px; border-radius: 6px;"></div>
							<div class="skel" style="height: 18px; width: 60px; border-radius: 20px;"></div>
						</div>
						<div class="skel" style="height: 14px; width: 80%; border-radius: 6px;"></div>
						<div style="display: flex; gap: 6px;">
							<div class="skel" style="height: 26px; width: 90px; border-radius: 6px;"></div>
							<div class="skel" style="height: 26px; width: 90px; border-radius: 6px;"></div>
							<div class="skel" style="height: 26px; width: 80px; border-radius: 6px;"></div>
						</div>
						<div style="display: flex; justify-content: space-between; padding-top: 4px;">
							<div class="skel" style="height: 14px; width: 100px; border-radius: 6px;"></div>
							<div class="skel" style="height: 28px; width: 60px; border-radius: 6px;"></div>
						</div>
					</div>
				</div>
			{/each}
		</div>

	{:else if scanEnginesStore.engines.length === 0}
		<!-- Empty state -->
		<div
			style="
				display: flex;
				flex-direction: column;
				align-items: center;
				justify-content: center;
				padding: 80px 24px;
				border: 1.5px dashed #e2e8f0;
				border-radius: 16px;
				background: #fafafa;
				text-align: center;
			"
		>
			<div
				style="
					width: 64px;
					height: 64px;
					border-radius: 16px;
					background: linear-gradient(135deg, #ede9ff 0%, #e0f7f1 100%);
					display: flex;
					align-items: center;
					justify-content: center;
					margin-bottom: 20px;
				"
			>
				<Network size={28} color="#7F77DD" />
			</div>
			<h2 style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 8px;">
				No scan engines yet
			</h2>
			<p style="font-size: 14px; color: #64748b; max-width: 400px; line-height: 1.6; margin: 0 0 24px;">
				Scan engines define which tools run, in which order, and with what configuration.
				Create your first engine to get started.
			</p>
			<div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: center;">
				<Button onclick={handleNewEngine} class="gap-2">
					<Plus size={15} />
					Create Your First Engine
				</Button>
				<div
					style="
						display: flex;
						align-items: center;
						gap: 6px;
						padding: 4px 12px;
						background: #fff7ed;
						border: 1px solid #fed7aa;
						border-radius: 20px;
						font-size: 12px;
						color: #c2410c;
						font-weight: 500;
					"
				>
					<Zap size={12} />
					3 recon phases: Discovery &rarr; Expansion &rarr; Depth
				</div>
			</div>
		</div>

	{:else}
		<!-- Engine grid -->
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

<style>
	.skel {
		background: #f1f5f9;
		animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}
</style>
