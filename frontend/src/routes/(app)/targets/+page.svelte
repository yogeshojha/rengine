<script lang="ts">
	import { untrack } from 'svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
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
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import PageSizeSelector from '$lib/components/targets/page-size-selector.svelte';

	let showAddModal = $state(false);
	let showDetailDialog = $state(false);
	let showDeleteDialog = $state(false);
	let selectedTarget = $state<Target | null>(null);
	let targetToDelete = $state<Target | null>(null);
	let isRefreshing = $state(false);
	let isDeleting = $state(false);

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

	async function handleTabChange(tab: string) {
		await targetsStore.setActiveTab(tab);
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

	async function handlePageChange(page: number) {
		await targetsStore.setPage(page);
	}

	async function handlePageSizeChange(size: number) {
		await targetsStore.setPageSize(size);
	}

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

	let showPagination = $derived(
		targetsStore.pagination.pageSize !== -1 &&
		targetsStore.pagination.totalPages > 1
	);
</script>

<div class="space-y-6">
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

	<TargetTypeTabs
		counts={targetsStore.counts}
		activeTab={targetsStore.filters.activeTab}
		onTabChange={handleTabChange}
	/>

	<Card.Root class="overflow-hidden">
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

			<div class="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="text-xs text-muted-foreground">
						Showing {targetsStore.filteredTargets.length} of {targetsStore.pagination.totalItems} targets
					</div>
					<PageSizeSelector
						pageSize={targetsStore.pagination.pageSize}
						onPageSizeChange={handlePageSizeChange}
					/>
				</div>

				{#if showPagination}
					<Pagination.Root
						count={targetsStore.pagination.totalItems}
						perPage={targetsStore.pagination.pageSize}
						page={targetsStore.pagination.currentPage}
						onPageChange={(page) => handlePageChange(page)}
					>
						{#snippet children({ pages, currentPage })}
							<Pagination.Content>
								<Pagination.Item>
									<Pagination.Previous />
								</Pagination.Item>
								{#each pages as page (page.key)}
									{#if page.type === "ellipsis"}
										<Pagination.Item>
											<Pagination.Ellipsis />
										</Pagination.Item>
									{:else}
										<Pagination.Item>
											<Pagination.Link {page} isActive={currentPage === page.value}>
												{page.value}
											</Pagination.Link>
										</Pagination.Item>
									{/if}
								{/each}
								<Pagination.Item>
									<Pagination.Next />
								</Pagination.Item>
							</Pagination.Content>
						{/snippet}
					</Pagination.Root>
				{/if}
			</div>
		{/if}
	</Card.Root>
</div>

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
