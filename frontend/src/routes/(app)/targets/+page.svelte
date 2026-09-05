<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ActivityLog } from '$lib/types/activity';
	import { targetsApi } from '$lib/api/targets';
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import Upload from '@lucide/svelte/icons/upload';
	import Play from '@lucide/svelte/icons/play';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
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
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import WhoisDetailDialog from '$lib/components/whois/whois-detail-dialog.svelte';
	import BgpDetailDialog from '$lib/components/bgp-ripestat-modal/bgp-detail-dialog.svelte';
	import { downloadTargets, type ExportFormat } from '$lib/utilities/target-export';
	import type { SignalFilter, SortDir, SortKey } from '$lib/utilities/target-signals';
	import { TaskStatus } from '$lib/types/task-status';
	import { browser } from '$app/environment';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/stores';
	import TargetViewsMenu from '$lib/components/targets/target-views-menu.svelte';
	import { ROUTES } from '$lib/config/routes';

	type EnrichmentKind = 'whois' | 'dns' | 'bgp';

	let urlReady = $state(false);

	function parseQuery(params: URLSearchParams) {
		const n = (v: string | null) => {
			const parsed = parseInt(v ?? '', 10);
			return Number.isFinite(parsed) ? parsed : undefined;
		};
		return {
			search: params.get('q') ?? undefined,
			activeTab: params.get('type') ?? undefined,
			signalFilter: (params.get('signal') as SignalFilter) || null,
			sortKey: (params.get('sort') as SortKey) || undefined,
			sortDir: (params.get('dir') as SortDir) || undefined,
			selectedOrganizations: params.getAll('org'),
			selectedTags: params.getAll('tag'),
			page: n(params.get('page')),
			pageSize: n(params.get('size'))
		};
	}

	function handleApplyView(query: string) {
		targetsStore.applyQueryState(parseQuery(new URLSearchParams(query)));
		targetsStore.reload();
	}

	let showAddModal = $state(false);
	let prefillValue = $state('');
	$effect(() => {
		if (!showAddModal) prefillValue = '';
	});
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

	const selectedTargetIds = new SvelteSet<string>();

	function setSelection(ids: Iterable<string> = []) {
		selectedTargetIds.clear();
		for (const id of ids) selectedTargetIds.add(id);
	}

	let deleteMode = $state<'single' | 'bulk'>('single');

	let showScanHistoryModal = $state(false);
	let scanHistoryTarget = $state<Target | null>(null);

	let showLaunchModal = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let launchTargetIds = $state<string[] | undefined>(undefined);

	let showScheduleModal = $state(false);
	let scheduleTargetId = $state<string | undefined>(undefined);

	let showEnrichConfirm = $state(false);
	let enrichConfirmKind = $state<EnrichmentKind>('whois');

	$effect(() => {
		const activeProject = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (activeProject && hasFetched) {
			untrack(() => {
				if (!urlReady) {
					targetsStore.applyQueryState(parseQuery($page.url.searchParams));
					urlReady = true;
				}
				targetsStore.fetchAll(activeProject.slug);
			});
		}
	});

	$effect(() => {
		const qs = targetsStore.toQueryString();
		if (!urlReady || !browser) return;
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	$effect(() => {
		const activeProject = projectsStore.activeProject;
		if (!activeProject) return;

		const unsub = sseStore.on<ActivityLog>(
			SSEChannel.project(activeProject.id),
			SSEEventType.ACTIVITY,
			async (event) => {
				if (!event.target_id) return;
				const type = event.event_type ?? '';

				if (!type.includes('.completed')) return;

				try {
					const fresh = await targetsApi.get(event.target_id);
					targetsStore.optimisticUpdateTarget(event.target_id, fresh);
				} catch {
					// ignore
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

	let selectedTargetValues = $derived(
		targetsStore.filteredTargets
			.filter((t) => selectedTargetIds.has(t.id))
			.map((t) => t.target_value)
	);

	const BULK_PREVIEW_LIMIT = 8;

	let deletePreviewValues = $derived(selectedTargetValues.slice(0, BULK_PREVIEW_LIMIT));
	let deletePreviewRemainder = $derived(
		Math.max(0, selectedTargetIds.size - deletePreviewValues.length)
	);

	let bulkDeletePreview = $derived(
		deletePreviewValues.length
			? ` Including: ${deletePreviewValues.join(', ')}${deletePreviewRemainder > 0 ? `, and ${deletePreviewRemainder} more` : ''}.`
			: ''
	);

	let deleteDialogDescription = $derived(
		deleteMode === 'single'
			? `This also deletes every scan and finding for ${targetToDelete?.target_value}.`
			: `This also deletes every scan and finding for ${selectedTargetIds.size} target${selectedTargetIds.size !== 1 ? 's' : ''}.${bulkDeletePreview}`
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

	const SIGNAL_LABELS: Record<SignalFilter, string> = {
		expiring: 'Expiring',
		attention: 'Needs attention',
		awaiting: 'Enriching',
		enriched: 'Enriched'
	};

	let activeChips = $derived.by(() => {
		const chips: { key: string; label: string; color?: string; remove: () => void }[] = [];
		const f = targetsStore.filters;
		if (f.searchQuery.trim()) {
			chips.push({
				key: 'q',
				label: `"${f.searchQuery.trim()}"`,
				remove: () => targetsStore.setSearchQuery('')
			});
		}
		for (const id of f.selectedOrganizations) {
			const org = organizationSummaries.find((o) => o.id === id);
			chips.push({
				key: `org-${id}`,
				label: org?.name ?? 'Org',
				remove: () => targetsStore.toggleOrganization(id)
			});
		}
		for (const id of f.selectedTags) {
			const tag = tagSummaries.find((t) => t.id === id);
			chips.push({
				key: `tag-${id}`,
				label: tag?.name ?? 'Tag',
				color: tag?.color,
				remove: () => targetsStore.toggleTag(id)
			});
		}
		if (f.signalFilter) {
			chips.push({
				key: 'signal',
				label: SIGNAL_LABELS[f.signalFilter],
				remove: () => targetsStore.setSignalFilter(null)
			});
		}
		return chips;
	});
	function openLaunch(targetId?: string) {
		launchTargetId = targetId;
		launchTargetIds = undefined;
		showLaunchModal = true;
	}

	function openLaunchMany(ids: string[]) {
		launchTargetId = undefined;
		launchTargetIds = ids;
		showLaunchModal = true;
	}

	function handleScan(target: Target) {
		openLaunch(target.id);
	}

	function handleSchedule(target: Target) {
		scheduleTargetId = target.id;
		showScheduleModal = true;
	}

	function handleScanAll() {
		openLaunchMany(targetsStore.filteredTargets.map((t) => t.id));
	}

	function handleTargetSelect(targetId: string) {
		if (selectedTargetIds.has(targetId)) selectedTargetIds.delete(targetId);
		else selectedTargetIds.add(targetId);
	}

	function handleSelectAll() {
		setSelection(
			selectedTargetIds.size >= targetsStore.filteredTargets.length
				? []
				: targetsStore.filteredTargets.map((t) => t.id)
		);
	}

	function clearSelection() {
		setSelection();
	}

	function handleBulkScan() {
		openLaunchMany(Array.from(selectedTargetIds));
	}

	function handleBulkDelete() {
		deleteMode = 'bulk';
		showDeleteDialog = true;
	}

	const BULK_ENRICH_CONFIRM_THRESHOLD = 25;

	async function runBulkEnrich(kind: EnrichmentKind) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkEnrich(ids, kind);
			toast.success(`Queued ${kind.toUpperCase()} for ${n} target${n !== 1 ? 's' : ''}`);
		} catch {
			toast.error(`Failed to queue ${kind.toUpperCase()} enrichment`);
		}
	}

	function handleBulkEnrich(kind: EnrichmentKind) {
		if (selectedTargetIds.size === 0) return;
		if (selectedTargetIds.size >= BULK_ENRICH_CONFIRM_THRESHOLD) {
			enrichConfirmKind = kind;
			showEnrichConfirm = true;
			return;
		}
		runBulkEnrich(kind);
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
		setSelection(ids);
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
		prefillValue = value;
		showAddModal = true;
	}

	async function confirmDelete() {
		isDeleting = true;

		if (deleteMode === 'single') {
			if (!targetToDelete) return;
			const success = await targetsStore.deleteTarget(targetToDelete.id);
			isDeleting = false;

			if (success) {
				toast.success('Target deleted');
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
			setSelection();
		}
	}

	async function handleRefresh() {
		isRefreshing = true;
		await targetsStore.refresh();
		isRefreshing = false;
		if (targetsStore.error) toast.error(`Refresh failed — ${targetsStore.error}`);
		else toast.success('Data refreshed');
	}

	async function handleTabChange(tab: string) {
		await targetsStore.setActiveTab(tab);
		setSelection();
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
		setSelection();
	}

	async function handlePageSizeChange(size: number) {
		await targetsStore.setPageSize(size);
		setSelection();
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
					<Play class="h-4 w-4" />
					Scan all ({targetsStore.filteredTargets.length})
				</Button>
			{/if}

			<Button variant="outline" onclick={() => (showImportModal = true)} class="gap-2">
				<Upload class="h-4 w-4" />
				Import
			</Button>

			<Button onclick={() => (showAddModal = true)} class="gap-2">
				<Plus class="h-4 w-4" />
				Add target
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
			<TargetViewsMenu currentQuery={targetsStore.toQueryString()} onApply={handleApplyView} />
			<TargetViewControls
				sortKey={targetsStore.filters.sortKey}
				sortDir={targetsStore.filters.sortDir}
				onSort={handleSort}
				onExport={handleExport}
				exportDisabled={targetsStore.filteredTargets.length === 0}
			/>
		</div>

		{#if activeChips.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b bg-muted/10">
				{#each activeChips as chip (chip.key)}
					<Badge variant="outline" class="gap-1 bg-background font-normal">
						{#if chip.color}
							<span class="h-2 w-2 rounded-full" style="background-color: {chip.color}"></span>
						{/if}
						{chip.label}
						<Tooltip.Provider delayDuration={300}>
							<Tooltip.Root>
								<Tooltip.Trigger
									class="rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
									onclick={chip.remove}
									aria-label={`Remove filter ${chip.label}`}
								>
									<X class="h-3 w-3" />
									<span class="sr-only">Remove filter {chip.label}</span>
								</Tooltip.Trigger>
								<Tooltip.Content>Remove filter {chip.label}</Tooltip.Content>
							</Tooltip.Root>
						</Tooltip.Provider>
					</Badge>
				{/each}
				<button
					class="ml-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					onclick={handleClearFilters}
					aria-label="Clear all filters"
				>
					Clear all
				</button>
			</div>
		{/if}

		{#if targetsStore.isLoading}
			<TargetListSkeleton count={8} />
		{:else if targetsStore.error && targetsStore.filteredTargets.length === 0}
			<Empty.Root class="py-16">
				<Empty.Header>
					<Empty.Media class="size-12 rounded-2xl bg-destructive/10">
						<TriangleAlert class="size-6 text-destructive" />
					</Empty.Media>
					<Empty.Title>Couldn't load targets</Empty.Title>
					<Empty.Description class="max-w-md">{targetsStore.error}</Empty.Description>
				</Empty.Header>
				<Empty.Content>
					<Button variant="outline" class="gap-2" onclick={() => targetsStore.reload()}>
						<RefreshCw class="h-4 w-4" />
						Retry
					</Button>
				</Empty.Content>
			</Empty.Root>
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
						isSelected={selectedTargetIds.has(target.id)}
						isScanning={false}
						onSelect={handleTargetSelect}
						onScan={handleScan}
						onSchedule={handleSchedule}
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

<AddTargetModal bind:open={showAddModal} initialValue={prefillValue} />
<ImportTargetsModal bind:open={showImportModal} />

<LaunchDialog
	bind:open={showLaunchModal}
	targetId={launchTargetId}
	targetIds={launchTargetIds}
	onClose={() => {
		showLaunchModal = false;
		launchTargetId = undefined;
		launchTargetIds = undefined;
	}}
/>

<ScheduleModal
	bind:open={showScheduleModal}
	presetTargetIds={scheduleTargetId ? [scheduleTargetId] : undefined}
	onClose={() => {
		showScheduleModal = false;
		scheduleTargetId = undefined;
	}}
/>

<TargetDetailDialog
	bind:open={showDetailDialog}
	target={selectedTarget}
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
		goto(ROUTES.target(whoisTarget?.id ?? ''));
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

<AlertDialog.Root bind:open={showEnrichConfirm}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>
				Re-run {enrichConfirmKind.toUpperCase()} for {selectedTargetIds.size} targets?
			</AlertDialog.Title>
			<AlertDialog.Description>
				This queues {enrichConfirmKind.toUpperCase()} enrichment across {selectedTargetIds.size} selected
				targets and may take a while. Lookups are rate-limited.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={() => runBulkEnrich(enrichConfirmKind)}>
				Queue {enrichConfirmKind.toUpperCase()}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
