<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import Hint from '$lib/components/hint.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import History from '@lucide/svelte/icons/history';
	import Layers from '@lucide/svelte/icons/layers';
	import List from '@lucide/svelte/icons/list';

	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import ConfirmDialog from '@/components/confirm-dialog.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		SCAN_STATUS_TABS,
		SCAN_POLL_MS,
		isLiveStatus,
		scanStatusTab
	} from '$lib/utilities/scan-status';
	import { NOW_TICK_MS } from '$lib/constants';
	import { SCAN_TIME_RANGES } from '$lib/types/scan';
	import { downloadScans, type ExportFormat } from '$lib/utilities/scan-export';
	import type { ScanRead } from '$lib/types/scan';

	import ScanFilters from './scan-filters.svelte';
	import ScanStatusTabs from './scan-status-tabs.svelte';
	import ScanViewControls from './scan-view-controls.svelte';
	import ScanListHeader from './scan-list-header.svelte';
	import ScanListItem from './scan-list-item.svelte';
	import ScanTargetGroupRow from './scan-target-group.svelte';
	import ScanBulkActionBar from './scan-bulk-action-bar.svelte';
	import PageSizeSelector from '$lib/components/targets/page-size-selector.svelte';

	interface Props {
		targetId?: string;
		onLaunch?: () => void;
		onRescan?: (scan: ScanRead) => void;
		onRescanMany?: (targetIds: string[]) => void;
	}

	let { targetId, onLaunch, onRescan, onRescanMany }: Props = $props();

	let cancelTarget = $state<ScanRead | null>(null);
	let deleteTarget = $state<ScanRead | null>(null);
	let bulkDeleteOpen = $state(false);
	let bulkCancelOpen = $state(false);
	let now = $state(Date.now());

	const selectedScanIds = new SvelteSet<string>();

	$effect(() => {
		const project = projectsStore.activeProject;
		const tid = targetId;
		if (project && projectsStore.hasFetched) {
			untrack(() => scansStore.init(project.id, tid));
		}
	});

	$effect(() => {
		if (!scansStore.hasLive) return;
		const tick = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		const poll = setInterval(() => scansStore.refresh(), SCAN_POLL_MS);
		return () => {
			clearInterval(tick);
			clearInterval(poll);
		};
	});

	$effect(() => {
		if (scansStore.hasLive) engineCatalogStore.fetch();
	});

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => scansStore.refresh());
	});

	let scans = $derived(scansStore.scans);
	let groups = $derived(scansStore.targetGroups);
	let grouped = $derived(scansStore.groupByTarget);
	let rowCount = $derived(grouped ? groups.length : scans.length);
	let pagination = $derived(scansStore.pagination);
	let showPagination = $derived(pagination.pageSize !== -1 && pagination.totalPages > 1);
	let statusTab = $derived(scanStatusTab(scansStore.filters.statuses));

	let selectedScans = $derived(scans.filter((s) => selectedScanIds.has(s.id)));
	let selectedLiveCount = $derived(selectedScans.filter((s) => isLiveStatus(s.status)).length);
	let selectedTargetIds = $derived([...new Set(selectedScans.map((s) => s.target_id))]);
	let selectAllChecked = $derived<boolean | 'indeterminate'>(
		scans.length > 0 && selectedScans.length === scans.length
			? true
			: selectedScans.length > 0
				? 'indeterminate'
				: false
	);

	$effect(() => {
		const ids = new Set(scans.map((s) => s.id));
		for (const id of selectedScanIds) {
			if (!ids.has(id)) selectedScanIds.delete(id);
		}
	});

	function toggleScan(id: string) {
		if (selectedScanIds.has(id)) selectedScanIds.delete(id);
		else selectedScanIds.add(id);
	}

	function toggleSelectAll() {
		if (selectedScans.length === scans.length) selectedScanIds.clear();
		else for (const s of scans) selectedScanIds.add(s.id);
	}

	function clearSelection() {
		selectedScanIds.clear();
	}

	function setView(view: string) {
		if (!view) return;
		if ((view === 'targets') !== grouped) scansStore.toggleGroupByTarget();
	}

	async function confirmBulkDelete() {
		const ids = [...selectedScanIds];
		bulkDeleteOpen = false;
		if (ids.length === 0) return;
		const { ok, failed } = await scansStore.removeMany(ids);
		selectedScanIds.clear();
		if (ok > 0) toast.success(`Deleted ${ok} scan${ok !== 1 ? 's' : ''}`);
		if (failed > 0) toast.error(`${failed} scan${failed !== 1 ? 's' : ''} could not be deleted`);
	}

	async function confirmBulkCancel() {
		const ids = selectedScans.filter((s) => isLiveStatus(s.status)).map((s) => s.id);
		bulkCancelOpen = false;
		if (ids.length === 0) return;
		const { ok, failed } = await scansStore.cancelMany(ids);
		if (ok > 0) toast.success(`Cancelled ${ok} scan${ok !== 1 ? 's' : ''}`);
		if (failed > 0) toast.error(`${failed} scan${failed !== 1 ? 's' : ''} could not be cancelled`);
	}

	let activeChips = $derived.by(() => {
		const chips: { key: string; label: string; remove: () => void }[] = [];
		const f = scansStore.filters;
		if (f.search.trim()) {
			chips.push({
				key: 'q',
				label: `"${f.search.trim()}"`,
				remove: () => scansStore.setSearch('')
			});
		}
		for (const e of f.engines) {
			chips.push({ key: `engine-${e}`, label: e, remove: () => scansStore.toggleEngine(e) });
		}
		for (const c of f.contexts) {
			chips.push({ key: `context-${c}`, label: c, remove: () => scansStore.toggleContext(c) });
		}
		if (f.timeRange !== 'all') {
			chips.push({
				key: 'time',
				label: SCAN_TIME_RANGES.find((r) => r.key === f.timeRange)?.label ?? 'Time',
				remove: () => scansStore.setTimeRange('all')
			});
		}
		if (f.scheduled !== null) {
			chips.push({
				key: 'scheduled',
				label: f.scheduled ? 'Scheduled only' : 'Manual only',
				remove: () => scansStore.setScheduleMode('all')
			});
		}
		return chips;
	});

	let exporting = $state(false);

	async function handleExport(format: ExportFormat) {
		if (pagination.totalItems === 0 || exporting) {
			if (!exporting) toast.error('Nothing to export in the current view');
			return;
		}
		exporting = true;
		try {
			const rows = await scansStore.exportAll();
			if (rows.length === 0) {
				toast.error('Nothing to export in the current view');
				return;
			}
			downloadScans(rows, format);
			const capped = rows.length < pagination.totalItems;
			toast.success(
				capped
					? `Exported the first ${rows.length} of ${pagination.totalItems} scans as ${format.toUpperCase()}`
					: `Exported ${rows.length} scan${rows.length !== 1 ? 's' : ''} as ${format.toUpperCase()}`
			);
		} catch {
			toast.error('Scans could not be exported');
		} finally {
			exporting = false;
		}
	}

	async function confirmCancel() {
		const s = cancelTarget;
		cancelTarget = null;
		if (s && (await scansStore.cancel(s))) toast.success('Scan cancelled');
		else if (s) toast.error(scansStore.error ?? 'Scan could not be cancelled');
	}

	async function confirmDelete() {
		const s = deleteTarget;
		deleteTarget = null;
		if (s && (await scansStore.remove(s))) toast.success('Scan deleted');
		else if (s) toast.error(scansStore.error ?? 'Scan could not be deleted');
	}
</script>

{#snippet pager()}
	{#if showPagination}
		<Pagination.Root
			count={pagination.totalItems}
			perPage={pagination.pageSize}
			page={pagination.currentPage}
			onPageChange={(p) => scansStore.setPage(p)}
		>
			{#snippet children({ pages, currentPage })}
				<Pagination.Content>
					<Pagination.Item><Pagination.Previous /></Pagination.Item>
					{#each pages as p (p.key)}
						{#if p.type === 'ellipsis'}
							<Pagination.Item><Pagination.Ellipsis /></Pagination.Item>
						{:else}
							<Pagination.Item>
								<Pagination.Link page={p} isActive={currentPage === p.value}>
									{p.value}
								</Pagination.Link>
							</Pagination.Item>
						{/if}
					{/each}
					<Pagination.Item><Pagination.Next /></Pagination.Item>
				</Pagination.Content>
			{/snippet}
		</Pagination.Root>
	{/if}
{/snippet}

{#snippet footer(shown: number, noun: string)}
	<div class="flex items-center justify-between border-t bg-muted/20 px-4 py-3">
		<div class="flex items-center gap-4">
			<div class="text-xs text-muted-foreground">
				Showing {shown} of {pagination.totalItems}
				{noun}{pagination.totalItems !== 1 ? 's' : ''}
			</div>
			<PageSizeSelector
				pageSize={pagination.pageSize}
				onPageSizeChange={(size) => scansStore.setPageSize(size)}
			/>
		</div>
		{@render pager()}
	</div>
{/snippet}

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="border-b px-2">
		<ScanStatusTabs
			active={statusTab}
			counts={scansStore.stats?.by_status ?? null}
			total={scansStore.stats?.total ?? 0}
			onChange={(tab) =>
				scansStore.setStatuses(SCAN_STATUS_TABS.find((t) => t.key === tab)?.statuses ?? [])}
		/>
	</div>

	<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
		<div class="min-w-0 flex-1">
			<ScanFilters
				search={scansStore.filters.search}
				onSearchChange={(q) => scansStore.setSearch(q)}
				engines={scansStore.filters.engines}
				engineOptions={scansStore.engineOptions}
				onToggleEngine={(e) => scansStore.toggleEngine(e)}
				contexts={scansStore.filters.contexts}
				contextOptions={scansStore.contextOptions}
				onToggleContext={(c) => scansStore.toggleContext(c)}
				timeRange={scansStore.filters.timeRange}
				onTimeRange={(r) => scansStore.setTimeRange(r)}
				scheduleMode={scansStore.scheduleMode}
				onScheduleMode={(m) => scansStore.setScheduleMode(m)}
			/>
		</div>
		<div class="flex items-center gap-2">
			<Hint text="Rescans of individual assets. Hidden by default. They are not full runs.">
				{#snippet child(props)}
					<label
						{...props}
						class="flex cursor-pointer items-center gap-2 rounded-md border border-border px-2.5 py-2 text-xs text-muted-foreground hover:text-foreground"
					>
						<Checkbox
							checked={scansStore.includeFocused}
							onCheckedChange={(v) => scansStore.setIncludeFocused(v === true)}
							aria-label="Include focused rescans"
						/>
						Focused rescans
					</label>
				{/snippet}
			</Hint>
			{#if !targetId}
				<ToggleGroup.Root
					type="single"
					variant="outline"
					value={grouped ? 'targets' : 'runs'}
					onValueChange={setView}
					aria-label="View"
				>
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<ToggleGroup.Item {...props} value="runs" aria-label="List scans" class="h-9 px-3">
									<List class="h-4 w-4" />
								</ToggleGroup.Item>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>List scans</Tooltip.Content>
					</Tooltip.Root>
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<ToggleGroup.Item
									{...props}
									value="targets"
									aria-label="Group by target"
									class="h-9 px-3"
								>
									<Layers class="h-4 w-4" />
								</ToggleGroup.Item>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Group by target</Tooltip.Content>
					</Tooltip.Root>
				</ToggleGroup.Root>
			{/if}
			{#if !grouped}
				<ScanViewControls
					sortKey={scansStore.filters.sortKey}
					sortDir={scansStore.filters.sortDir}
					onSort={(k) => scansStore.setSort(k)}
					onExport={handleExport}
					exportDisabled={pagination.totalItems === 0 || exporting}
				/>
			{/if}
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9"
				aria-label="Refresh"
				onclick={() => scansStore.refresh()}
			>
				<RefreshCw class="h-4 w-4 {scansStore.refreshing ? 'animate-spin' : ''}" />
			</Button>
			{#if onLaunch}
				<Button class="h-9 gap-2" onclick={onLaunch}>
					<Plus class="h-4 w-4" /> New scan
				</Button>
			{/if}
		</div>
	</div>

	{#if activeChips.length > 0}
		<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
			{#each activeChips as chip (chip.key)}
				<Badge variant="outline" class="gap-1 bg-background font-normal">
					{chip.label}
					<Tooltip.Root>
						<Tooltip.Trigger
							class="rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							onclick={chip.remove}
							aria-label={`Remove filter ${chip.label}`}
						>
							<X class="h-3 w-3" />
							<span class="sr-only">Remove filter {chip.label}</span>
						</Tooltip.Trigger>
						<Tooltip.Content>Remove filter {chip.label}</Tooltip.Content>
					</Tooltip.Root>
				</Badge>
			{/each}
			<button
				class="ml-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				onclick={() => scansStore.clearFilters()}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if scansStore.isLoading && rowCount === 0}
		<div class="divide-y divide-border/50">
			{#each Array(8) as _, i (i)}
				<div class="flex items-center gap-3 px-4 py-3">
					<Skeleton class="h-9 flex-1" />
					<Skeleton class="hidden h-6 w-[120px] sm:block" />
					<Skeleton class="hidden h-6 w-[120px] sm:block" />
				</div>
			{/each}
		</div>
	{:else if scansStore.error && rowCount === 0}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Media class="size-12 rounded-2xl bg-destructive/10">
					<TriangleAlert class="size-6 text-destructive" />
				</Empty.Media>
				<Empty.Title>Scans could not be loaded</Empty.Title>
				<Empty.Description class="max-w-md">{scansStore.error}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button variant="outline" class="gap-2" onclick={() => scansStore.refresh()}>
					<RefreshCw class="h-4 w-4" /> Retry
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if rowCount === 0 && scansStore.hasActiveFilters}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Title>No scans match</Empty.Title>
				<Empty.Description>Widen the search or remove a filter.</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" class="gap-2" onclick={() => scansStore.clearFilters()}>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if rowCount === 0}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Media
					variant="icon"
					class="h-14 w-14 rounded-2xl bg-muted text-muted-foreground/60 [&_svg:not([class*='size-'])]:size-6"
				>
					<History />
				</Empty.Media>
				<Empty.Title>No scans yet</Empty.Title>
				<Empty.Description class="max-w-sm">
					Start a scan to build the run history.
				</Empty.Description>
			</Empty.Header>
			{#if onLaunch}
				<Empty.Content>
					<Button class="gap-2" onclick={onLaunch}>
						<Plus class="h-4 w-4" /> New scan
					</Button>
				</Empty.Content>
			{/if}
		</Empty.Root>
	{:else if grouped}
		<div class="divide-y divide-border/50">
			{#each groups as group (group.target_id)}
				<ScanTargetGroupRow
					{group}
					{now}
					loadScans={(tid) => scansStore.loadTargetScans(tid)}
					onRescan={(s) => onRescan?.(s)}
					onCancel={(s) => (cancelTarget = s)}
					onDelete={(s) => (deleteTarget = s)}
				/>
			{/each}
		</div>
		{@render footer(groups.length, 'target')}
	{:else}
		<ScanListHeader
			{targetId}
			selectable
			{selectAllChecked}
			onSelectAll={toggleSelectAll}
			sortKey={scansStore.filters.sortKey}
			sortDir={scansStore.filters.sortDir}
			onSort={(k) => scansStore.setSort(k)}
		/>

		<div class="divide-y divide-border/50">
			{#each scans as scan (scan.id)}
				<ScanListItem
					{scan}
					{targetId}
					{now}
					selectable
					isSelected={selectedScanIds.has(scan.id)}
					onSelect={toggleScan}
					onRescan={(s) => onRescan?.(s)}
					onCancel={(s) => (cancelTarget = s)}
					onDelete={(s) => (deleteTarget = s)}
				/>
			{/each}
		</div>
		{@render footer(scans.length, 'scan')}
	{/if}
</Card.Root>

<ConfirmDialog
	open={!!cancelTarget}
	title="Cancel this scan?"
	description="The scan will stop queuing further work and be marked cancelled."
	confirmLabel="Cancel scan"
	cancelLabel="Keep running"
	onOpenChange={(o) => !o && (cancelTarget = null)}
	onConfirm={confirmCancel}
/>

<ConfirmDialog
	open={!!deleteTarget}
	title="Delete this scan?"
	description="The scan and all of its results are removed."
	confirmLabel="Delete"
	cancelLabel="Keep"
	destructive
	onOpenChange={(o) => !o && (deleteTarget = null)}
	onConfirm={confirmDelete}
/>

{#if !grouped}
	<ScanBulkActionBar
		selectedCount={selectedScans.length}
		liveCount={selectedLiveCount}
		targetCount={selectedTargetIds.length}
		onRescan={() => {
			onRescanMany?.(selectedTargetIds);
			clearSelection();
		}}
		onCancel={() => (bulkCancelOpen = true)}
		onDelete={() => (bulkDeleteOpen = true)}
		onClear={clearSelection}
	/>
{/if}

<ConfirmDialog
	open={bulkDeleteOpen}
	title="Delete {selectedScans.length} scan{selectedScans.length !== 1 ? 's' : ''}?"
	description="The selected scans and all of their results are removed."
	confirmLabel="Delete {selectedScans.length}"
	cancelLabel="Keep"
	destructive
	onOpenChange={(o) => (bulkDeleteOpen = o)}
	onConfirm={confirmBulkDelete}
/>

<ConfirmDialog
	open={bulkCancelOpen}
	title="Cancel {selectedLiveCount} running scan{selectedLiveCount !== 1 ? 's' : ''}?"
	description="The selected running scans will stop queuing further work and be marked cancelled."
	confirmLabel="Cancel scans"
	cancelLabel="Keep running"
	onOpenChange={(o) => (bulkCancelOpen = o)}
	onConfirm={confirmBulkCancel}
/>
