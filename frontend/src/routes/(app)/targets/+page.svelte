<script lang="ts">
	import { untrack } from 'svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import { Button } from '$lib/components/ui/button';
	import { Upload, Play, Plus, RefreshCw } from 'lucide-svelte';
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
	import ScanHistoryModal from '$lib/components/targets/scan-history-modal.svelte';
	import BulkActionBar from '$lib/components/targets/bulk-action-bar.svelte';
	import ImportTargetsModal from '$lib/components/modals/import-targets-modal.svelte';
	import WhoisDetailDialog from '$lib/components/whois/whois-detail-dialog.svelte';
	import BgpDetailDialog from '$lib/components/bgp-ripestat-modal/bgp-detail-dialog.svelte';

	let showAddModal = $state(false);
	let showDetailDialog = $state(false);
	let showDeleteDialog = $state(false);
	let selectedTarget = $state<Target | null>(null);
	let targetToDelete = $state<Target | null>(null);
	let isDeleting = $state(false);
	let isRefreshing = $state(false);
	let showImportModal = $state(false);

	let showWhoisDialog = $state(false);
	let whoisTarget = $state<Target | null>(null);
	let whoisInitialTab = $state('overview');

	let showBgpDialog = $state(false);
	let bgpDialogTarget = $state<Target | null>(null);

	let activeScanCounts = $state<Record<string, number>>({});

	let selectedTargetIds = $state(new Set<string>());

	let deleteMode = $state<'single' | 'bulk'>('single');

	let showScanHistoryModal = $state(false);
	let scanHistoryTarget = $state<Target | null>(null);

	$effect(() => {
		const activeProject = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (activeProject && hasFetched) {
			untrack(() => {
				targetsStore.fetchAll(activeProject.slug);
			});
		}
	});

	let selectAllChecked = $derived<boolean | 'indeterminate'>(
		selectedTargetIds.size === 0
			? false
			: selectedTargetIds.size >= targetsStore.filteredTargets.length
				? true
				: 'indeterminate'
	);

	let deleteDialogTitle = $derived(
		deleteMode === 'single'
			? 'Delete Target'
			: `Delete ${selectedTargetIds.size} Target${selectedTargetIds.size !== 1 ? 's' : ''}`
	);

	let deleteDialogDescription = $derived(
		deleteMode === 'single'
			? `Are you sure you want to delete '${targetToDelete?.target_value}'? This action cannot be undone and will remove all associated scan data.`
			: `Are you sure you want to delete ${selectedTargetIds.size} selected target${selectedTargetIds.size !== 1 ? 's' : ''}? This action cannot be undone and will remove all associated data.`
	);

	let selectedTargetIsScanning = $derived(
		selectedTarget ? (activeScanCounts[selectedTarget.id] || 0) > 0 : false
	);

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
		targetsStore.pagination.pageSize !== -1 && targetsStore.pagination.totalPages > 1
	);
	function fireScan(target: Target) {
		activeScanCounts[target.id] = (activeScanCounts[target.id] || 0) + 1;
		// TODO: replace setTimeout with real API call
		setTimeout(() => {
			activeScanCounts[target.id] = Math.max(0, (activeScanCounts[target.id] || 0) - 1);
		}, 3000);
	}

	function handleScan(target: Target) {
		fireScan(target);
		toast.success(`Scan initiated for ${target.target_value}`);
	}

	function handleScanAll() {
		const targets = targetsStore.filteredTargets;
		if (targets.length === 0) return;
		targets.forEach(fireScan);
		toast.success(`Scans initiated for ${targets.length} target${targets.length !== 1 ? 's' : ''}`);
	}

	function handleTargetSelect(targetId: string) {
		const next = new Set(selectedTargetIds);
		next.has(targetId) ? next.delete(targetId) : next.add(targetId);
		selectedTargetIds = next;
	}

	function handleSelectAll() {
		selectedTargetIds =
			selectedTargetIds.size >= targetsStore.filteredTargets.length
				? new Set()
				: new Set(targetsStore.filteredTargets.map((t) => t.id));
	}

	function clearSelection() {
		selectedTargetIds = new Set();
	}

	function handleBulkScan() {
		const targets = targetsStore.filteredTargets.filter((t) => selectedTargetIds.has(t.id));
		targets.forEach(fireScan);
		toast.success(`Scans initiated for ${targets.length} target${targets.length !== 1 ? 's' : ''}`);
	}

	function handleBulkDelete() {
		deleteMode = 'bulk';
		showDeleteDialog = true;
	}

	function handleOpenScanHistory(target: Target) {
		scanHistoryTarget = target;
		showScanHistoryModal = true;
	}
	function handleViewTarget(target: Target) {
		selectedTarget = target;
		showDetailDialog = true;
	}

	function handleEditTarget(target: Target) {
		toast.info('todooo');
	}

	function handleDeleteTarget(target: Target) {
		targetToDelete = target;
		deleteMode = 'single';
		showDeleteDialog = true;
	}

	function handleWhoisClick(target: Target) {
		whoisTarget = target;
		whoisInitialTab = 'overview';
		showWhoisDialog = true;
	}

	function handleDiscoveriesClick(target: Target) {
		whoisTarget = target;
		whoisInitialTab = 'discoveries';
		showWhoisDialog = true;
	}

	function handleBgpClick(target: Target) {
		bgpDialogTarget = target;
		showBgpDialog = true;
	}

	function handleAddAsTarget(value: string) {
		showAddModal = true;
		// TODO: pre-fill the add target modal with `value`
		// This could be done via a store or by passing initialValue to AddTargetModal
		toast.info(`Add "${value}" as a new target`);
	}

	async function confirmDelete() {
		isDeleting = true;

		if (deleteMode === 'single') {
			if (!targetToDelete) return;
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
		} else {
			const ids = Array.from(selectedTargetIds);
			const results = await Promise.all(ids.map((id) => targetsStore.deleteTarget(id)));
			isDeleting = false;

			const ok = results.filter(Boolean).length;
			const fail = ids.length - ok;
			if (ok) toast.success(`${ok} target${ok !== 1 ? 's' : ''} deleted`);
			if (fail) toast.error(`Failed to delete ${fail} target${fail !== 1 ? 's' : ''}`);

			showDeleteDialog = false;
			selectedTargetIds = new Set();
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
		selectedTargetIds = new Set();
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
		selectedTargetIds = new Set();
	}

	async function handlePageSizeChange(size: number) {
		await targetsStore.setPageSize(size);
		selectedTargetIds = new Set();
	}
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

			{#if !targetsStore.isLoading && targetsStore.filteredTargets.length > 0}
				<Button variant="outline" size="sm" class="gap-2 h-9" onclick={handleScanAll}>
					<Play class="h-4 w-4 text-blue-400" />
					Scan All ({targetsStore.filteredTargets.length})
				</Button>
			{/if}

			<Button variant="outline" onclick={() => (showImportModal = true)} class="gap-2">
				<Upload class="h-4 w-4" />
				Import
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
			<TargetListHeader {selectAllChecked} onSelectAll={handleSelectAll} />

			<div class="divide-y divide-border/50">
				{#each targetsStore.filteredTargets as target (target.id)}
					<TargetListItem
						{target}
						isSelected={selectedTargetIds.has(target.id)}
						isScanning={(activeScanCounts[target.id] || 0) > 0}
						onSelect={handleTargetSelect}
						onScan={handleScan}
						onOpenHistory={handleOpenScanHistory}
						onView={handleViewTarget}
						onEdit={handleEditTarget}
						onDelete={handleDeleteTarget}
						onWhoisClick={handleWhoisClick}
						onDiscoveriesClick={handleDiscoveriesClick}
						onBgpClick={handleBgpClick}
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
									{#if page.type === 'ellipsis'}
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
<ImportTargetsModal bind:open={showImportModal} />

<TargetDetailDialog
	bind:open={showDetailDialog}
	target={selectedTarget}
	isScanning={selectedTargetIsScanning}
	onOpenChange={(open) => (showDetailDialog = open)}
	onScan={handleScan}
	onOpenHistory={handleOpenScanHistory}
	onEdit={handleEditTarget}
	onDelete={handleDeleteTarget}
/>

<ScanHistoryModal
	bind:open={showScanHistoryModal}
	target={scanHistoryTarget}
	onOpenChange={(open) => (showScanHistoryModal = open)}
/>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title={deleteDialogTitle}
	description={deleteDialogDescription}
	{isDeleting}
	onOpenChange={(open) => (showDeleteDialog = open)}
	onConfirm={confirmDelete}
/>

<BulkActionBar
	selectedCount={selectedTargetIds.size}
	onScan={handleBulkScan}
	onDelete={handleBulkDelete}
	onClear={clearSelection}
/>

<WhoisDetailDialog
	bind:open={showWhoisDialog}
	recordId={whoisTarget?.whois_record_id}
	targetId={whoisTarget?.id}
	targetValue={whoisTarget?.target_value}
	targetType={whoisTarget?.target_type}
	initialTab={whoisInitialTab}
	onOpenChange={(open) => (showWhoisDialog = open)}
	onOpenTargetSummary={() => {
		// TODO: navigate to /targets/:id?tab=discoveries
		// goto(`/targets/${whoisTarget?.id}?tab=discoveries`)
	}}
/>

<BgpDetailDialog
	bind:open={showBgpDialog}
	targetId={bgpDialogTarget?.id}
	targetValue={bgpDialogTarget?.target_value}
	targetType={bgpDialogTarget?.target_type}
	bgpSummary={bgpDialogTarget?.bgp}
	onOpenChange={(o) => (showBgpDialog = o)}
	onAddAsTarget={handleAddAsTarget}
/>
