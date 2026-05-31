<script lang="ts">
	import { untrack } from 'svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ActivityLog } from '$lib/types/activity';
	import { targetsApi } from '$lib/api/targets';
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import { Button } from '$lib/components/ui/button';
	import { Upload, Play, Plus, RefreshCw } from 'lucide-svelte';
	import { toast } from 'svelte-sonner';

	import TargetTypeTabs from '$lib/components/targets/target-type-tabs.svelte';
	import TargetFilters from '$lib/components/targets/target-filters.svelte';
	import TargetsKpiStrip from '$lib/components/targets/targets-kpi-strip.svelte';
	import TargetViewControls from '$lib/components/targets/target-view-controls.svelte';
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
	import { downloadTargets, type ExportFormat } from '$lib/utilities/target-export';
	import type { SignalFilter, SortKey } from '$lib/utilities/target-signals';
	import { TaskStatus } from '$lib/types/task-status';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';

	type EnrichmentKind = 'whois' | 'dns' | 'bgp';

	let density = $state<'comfortable' | 'compact'>(
		browser && localStorage.getItem('targets:density') === 'compact' ? 'compact' : 'comfortable'
	);

	function toggleDensity() {
		density = density === 'compact' ? 'comfortable' : 'compact';
		if (browser) localStorage.setItem('targets:density', density);
	}

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

	$effect(() => {
		const activeProject = projectsStore.activeProject;
		if (!activeProject) return;

		const unsub = sseStore.on<ActivityLog>(
			SSEChannel.project(activeProject.id),
			SSEEventType.ACTIVITY,
			async (event) => {
				if (!event.event_type?.includes('.completed')) return;
				if (!event.target_id) return;

				try {
					const fresh = await targetsApi.get(event.target_id);
					targetsStore.optimisticUpdateTarget(event.target_id, fresh);
				} catch {
					// Target may have been deleted, ignore
				}
			}
		);

		return unsub;
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

	async function handleBulkEnrich(kind: EnrichmentKind) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkEnrich(ids, kind);
			toast.success(`Queued ${kind.toUpperCase()} for ${n} target${n !== 1 ? 's' : ''}`);
		} catch {
			toast.error(`Failed to queue ${kind.toUpperCase()} enrichment`);
		}
	}

	async function handleBulkAddTag(name: string) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkAddTags(ids, [name]);
			toast.success(`Tagged ${n} target${n !== 1 ? 's' : ''} with "${name}"`);
		} catch {
			toast.error('Failed to add tag');
		}
	}

	async function handleBulkAddOrg(name: string) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkAddOrganizations(ids, [name]);
			toast.success(`Added ${n} target${n !== 1 ? 's' : ''} to "${name}"`);
		} catch {
			toast.error('Failed to add organization');
		}
	}

	async function handleSelectAllMatching() {
		const ids = await targetsStore.getMatchingIds();
		selectedTargetIds = new Set(ids);
		toast.success(`Selected all ${ids.length} matching target${ids.length !== 1 ? 's' : ''}`);
	}

	function handleOpenScanHistory(target: Target) {
		scanHistoryTarget = target;
		showScanHistoryModal = true;
	}
	function handleViewTarget(target: Target) {
		selectedTarget = target;
		showDetailDialog = true;
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

	function handleInfraClick(target: Target) {
		whoisTarget = target;
		whoisInitialTab = 'related';
		showWhoisDialog = true;
	}

	async function handleRename(target: Target, name: string) {
		const updated = await targetsStore.updateTarget(target.id, { display_name: name });
		if (updated) toast.success(`Renamed to "${name}"`);
		else toast.error('Rename failed');
	}

	async function handleReEnrich(target: Target, kind: EnrichmentKind) {
		try {
			if (kind === 'whois') await targetsApi.refreshWhois(target.id);
			else if (kind === 'dns') await targetsApi.refreshDns(target.id);
			else await targetsApi.refreshBgp(target.id);

			const patch: Partial<Target> =
				kind === 'whois'
					? { whois_status: TaskStatus.PENDING }
					: kind === 'dns'
						? { dns_status: TaskStatus.PENDING }
						: { bgp_status: TaskStatus.PENDING };
			targetsStore.optimisticUpdateTarget(target.id, patch);
			toast.success(`Re-running ${kind.toUpperCase()} for ${target.target_value}`);
		} catch {
			toast.error(`Failed to queue ${kind.toUpperCase()} enrichment`);
		}
	}

	function handleBgpClick(target: Target) {
		bgpDialogTarget = target;
		showBgpDialog = true;
	}

	function handleAddAsTarget(value: string) {
		showAddModal = true;
		// TODO: pre-fill add target modal with `value`
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

	function handleSignalSelect(signal: SignalFilter | null) {
		targetsStore.setSignalFilter(signal);
	}

	function handleSort(key: SortKey) {
		targetsStore.setSort(key);
	}

	function handleExport(format: ExportFormat) {
		const rows = targetsStore.filteredTargets;
		if (rows.length === 0) {
			toast.error('Nothing to export in the current view');
			return;
		}
		downloadTargets(rows, format);
		toast.success(
			`Exported ${rows.length} target${rows.length !== 1 ? 's' : ''} as ${format.toUpperCase()}`
		);
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

	{#if targetsStore.signalSummary.total > 0}
		<TargetsKpiStrip
			summary={targetsStore.signalSummary}
			activeSignal={targetsStore.filters.signalFilter}
			onSelect={handleSignalSelect}
		/>
	{/if}

	<Card.Root class="overflow-hidden">
		<div class="p-4 border-b flex items-center gap-3 flex-wrap">
			<div class="flex-1 min-w-0">
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
			<TargetViewControls
				sortKey={targetsStore.filters.sortKey}
				sortDir={targetsStore.filters.sortDir}
				{density}
				onSort={handleSort}
				onToggleDensity={toggleDensity}
				onExport={handleExport}
				exportDisabled={targetsStore.filteredTargets.length === 0}
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
			<TargetListHeader
				{selectAllChecked}
				onSelectAll={handleSelectAll}
				sortKey={targetsStore.filters.sortKey}
				sortDir={targetsStore.filters.sortDir}
				onSort={handleSort}
			/>

			<div class="divide-y divide-border/50">
				{#each targetsStore.filteredTargets as target (target.id)}
					<TargetListItem
						{target}
						{density}
						isSelected={selectedTargetIds.has(target.id)}
						isScanning={(activeScanCounts[target.id] || 0) > 0}
						onSelect={handleTargetSelect}
						onScan={handleScan}
						onOpenHistory={handleOpenScanHistory}
						onView={handleViewTarget}
						onDelete={handleDeleteTarget}
						onRename={handleRename}
						onReEnrich={handleReEnrich}
						onWhoisClick={handleWhoisClick}
						onDiscoveriesClick={handleDiscoveriesClick}
						onBgpClick={handleBgpClick}
						onInfraClick={handleInfraClick}
					/>
				{/each}
			</div>

			<div class="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="text-xs text-muted-foreground">
						Showing {targetsStore.filteredTargets.length} of {targetsStore.pagination.totalItems} targets
					</div>
					{#if selectedTargetIds.size >= targetsStore.filteredTargets.length && selectedTargetIds.size < targetsStore.pagination.totalItems}
						<button
							class="text-xs font-medium text-primary hover:underline"
							onclick={handleSelectAllMatching}
						>
							Select all {targetsStore.pagination.totalItems} matching
						</button>
					{/if}
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
	tags={tagSummaries}
	organizations={organizationSummaries}
	onScan={handleBulkScan}
	onDelete={handleBulkDelete}
	onClear={clearSelection}
	onEnrich={handleBulkEnrich}
	onAddTag={handleBulkAddTag}
	onAddOrg={handleBulkAddOrg}
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
		goto(`/targets/${whoisTarget?.id}`);
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
