<script lang="ts">
	import { untrack } from 'svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Plus, RefreshCw } from 'lucide-svelte';
	import { toast } from 'svelte-sonner';

	import TargetTypeTabs from '$lib/components/targets/target-type-tabs.svelte';
	import TargetFilters from '$lib/components/targets/target-filters.svelte';
	import TargetListItem from '$lib/components/targets/target-list-item.svelte';
	import TargetListHeader from '$lib/components/targets/target-list-header.svelte';
	import TargetListSkeleton from '$lib/components/targets/target-list-skeleton.svelte';
	import TargetEmptyState from '$lib/components/targets/target-empty-state.svelte';
	import TargetDetailDialog from '$lib/components/targets/target-detail-dialog.svelte';
	import DeleteConfirmationDialog from '$lib/components/ui/delete-confirmation-dialog.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';

	// Local state
	let showAddModal = $state(false);
	let showDetailDialog = $state(false);
	let showDeleteDialog = $state(false);
	let selectedTarget = $state<Target | null>(null);
	let targetToDelete = $state<Target | null>(null);
	let isRefreshing = $state(false);
	let isDeleting = $state(false);

	// this changes the targets when active project changes
	$effect(() => {
		const activeProject = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;

		if (activeProject && hasFetched) {
			untrack(() => {
				targetsStore.fetchAll(activeProject.slug);
			});
		}
	});

	function handleViewTarget(target: Target) {
		selectedTarget = target;
		showDetailDialog = true;
	}

	function handleEditTarget(target: Target) {
		// TODO: Implement edit modal
		toast.info('todooo');
	}

	function handleDeleteTarget(target: Target) {
		targetToDelete = target;
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		if (!targetToDelete) return;

		isDeleting = true;
		const success = await targetsStore.deleteTarget(targetToDelete.id);
		isDeleting = false;

		if (success) {
			toast.success('Target deleted successfully');
			showDeleteDialog = false;
			showDetailDialog = false;
			targetToDelete = null;
		} else {
			toast.error('Failed to delete target');
		}
	}

	async function handleRefresh() {
		isRefreshing = true;
		await targetsStore.refresh();
		isRefreshing = false;
		toast.success('Data refreshed');
	}

	function handleTabChange(tab: string) {
		targetsStore.setActiveTab(tab);
	}

	function handleSearchChange(query: string) {
		targetsStore.setSearchQuery(query);
	}

	function handleOrganizationToggle(orgId: string) {
		targetsStore.toggleOrganization(orgId);
	}

	function handleTagToggle(tagId: string) {
		targetsStore.toggleTag(tagId);
	}

	function handleClearFilters() {
		targetsStore.clearFilters();
	}

	// Convert organizations/tags for filter component
	let organizationSummaries = $derived(
		targetsStore.organizations.map((org) => ({
			id: org.id,
			name: org.name,
			slug: org.slug
		}))
	);

	let tagSummaries = $derived(
		targetsStore.tags.map((tag) => ({
			id: tag.id,
			name: tag.name,
			slug: tag.slug,
			color: tag.color
		}))
	);
</script>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-start justify-between">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">Targets</h1>
			<p class="text-sm text-muted-foreground mt-1">
				Manage your attack surface assets across domains, IPs, and networks
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
			<Button onclick={() => (showAddModal = true)} class="gap-2">
				<Plus class="h-4 w-4" />
				Add Target
			</Button>
		</div>
	</div>

	<!-- Type Tabs -->
	<TargetTypeTabs
		counts={targetsStore.counts}
		activeTab={targetsStore.filters.activeTab}
		onTabChange={handleTabChange}
	/>

	<!-- Main Content Card -->
	<Card.Root class="overflow-hidden">
		<!-- Filters -->
		<div class="p-4 border-b">
			<TargetFilters
				searchQuery={targetsStore.filters.searchQuery}
				onSearchChange={handleSearchChange}
				organizations={organizationSummaries}
				selectedOrganizations={targetsStore.filters.selectedOrganizations}
				onOrganizationToggle={handleOrganizationToggle}
				tags={tagSummaries}
				selectedTags={targetsStore.filters.selectedTags}
				onTagToggle={handleTagToggle}
				onClearFilters={handleClearFilters}
			/>
		</div>

		<!-- List -->
		{#if targetsStore.isLoading}
			<TargetListSkeleton count={8} />
		{:else if targetsStore.filteredTargets.length === 0}
			<TargetEmptyState
				hasFilters={targetsStore.hasActiveFilters}
				onAddTarget={() => (showAddModal = true)}
				onClearFilters={handleClearFilters}
			/>
		{:else}
			<TargetListHeader />
			<div class="divide-y divide-border/50">
				{#each targetsStore.filteredTargets as target (target.id)}
					<TargetListItem
						{target}
						onView={handleViewTarget}
						onEdit={handleEditTarget}
						onDelete={handleDeleteTarget}
					/>
				{/each}
			</div>

			<!-- Footer with count -->
			<div class="px-4 py-3 border-t bg-muted/20 text-xs text-muted-foreground">
				Showing {targetsStore.filteredTargets.length} of {targetsStore.targets.length} targets
			</div>
		{/if}
	</Card.Root>
</div>

<!-- modals and dialogs here -->

<AddTargetModal bind:open={showAddModal} />

<TargetDetailDialog
	bind:open={showDetailDialog}
	target={selectedTarget}
	onOpenChange={(open) => (showDetailDialog = open)}
	onEdit={handleEditTarget}
	onDelete={handleDeleteTarget}
/>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title="Delete Target"
	description="Are you sure you want to delete '{targetToDelete?.target_value}'? This action cannot be undone and will remove all associated scan data."
	{isDeleting}
	onOpenChange={(open) => (showDeleteDialog = open)}
	onConfirm={confirmDelete}
/>
