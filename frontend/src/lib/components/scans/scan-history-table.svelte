<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Plus, RefreshCw, X, TriangleAlert, History, Layers } from 'lucide-svelte';

	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { SCAN_STATUS_LABEL, SCAN_POLL_MS } from '$lib/utilities/scan-status';
	import { SCAN_TIME_RANGES } from '$lib/types/scan';
	import { downloadScans, type ExportFormat } from '$lib/utilities/scan-export';
	import type { ScanRead } from '$lib/types/scan';

	import ScanInsights from './scan-insights.svelte';
	import ScanFilters from './scan-filters.svelte';
	import ScanViewControls from './scan-view-controls.svelte';
	import ScanListHeader from './scan-list-header.svelte';
	import ScanListItem from './scan-list-item.svelte';
	import ScanTargetGroupRow from './scan-target-group.svelte';
	import PageSizeSelector from '$lib/components/targets/page-size-selector.svelte';

	interface Props {
		targetId?: string;
		showSummary?: boolean;
		onLaunch?: () => void;
		onRescan?: (scan: ScanRead) => void;
	}

	let { targetId, showSummary = false, onLaunch, onRescan }: Props = $props();

	let cancelTarget = $state<ScanRead | null>(null);
	let deleteTarget = $state<ScanRead | null>(null);
	let now = $state(Date.now());

	$effect(() => {
		const project = projectsStore.activeProject;
		const tid = targetId;
		if (project && projectsStore.hasFetched) {
			untrack(() => scansStore.init(project.id, tid));
		}
	});

	$effect(() => {
		if (!scansStore.hasLive) return;
		const tick = setInterval(() => (now = Date.now()), 1000);
		const poll = setInterval(() => scansStore.refresh(), SCAN_POLL_MS);
		return () => {
			clearInterval(tick);
			clearInterval(poll);
		};
	});

	let scans = $derived(scansStore.scans);
	let groups = $derived(scansStore.targetGroups);
	let grouped = $derived(scansStore.groupByTarget);
	let rowCount = $derived(grouped ? groups.length : scans.length);
	let pagination = $derived(scansStore.pagination);
	let showPagination = $derived(pagination.pageSize !== -1 && pagination.totalPages > 1);

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
		for (const s of f.statuses) {
			chips.push({
				key: `status-${s}`,
				label: SCAN_STATUS_LABEL[s],
				remove: () => scansStore.toggleStatus(s)
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
			toast.error('Failed to export scans');
		} finally {
			exporting = false;
		}
	}

	async function confirmCancel() {
		const s = cancelTarget;
		cancelTarget = null;
		if (s && (await scansStore.cancel(s))) toast.success('Scan cancelled.');
		else if (s) toast.error(scansStore.error ?? 'Failed to cancel scan');
	}

	async function confirmDelete() {
		const s = deleteTarget;
		deleteTarget = null;
		if (s && (await scansStore.remove(s))) toast.success('Scan deleted.');
		else if (s) toast.error(scansStore.error ?? 'Failed to delete scan');
	}
</script>

<div class="space-y-3">
	{#if showSummary && !scansStore.isLoading && !scansStore.error}
		<ScanInsights
			stats={scansStore.stats}
			changes={scansStore.changes}
			changeWindow={scansStore.changeWindow}
			onWindow={(w) => scansStore.setChangeWindow(w)}
			onFilterStatus={(s) => scansStore.setStatuses(s)}
		/>
	{/if}

	<Card.Root class="overflow-hidden">
		<div class="p-4 border-b flex items-center gap-3 flex-wrap">
			<div class="flex-1 min-w-0">
				<ScanFilters
					search={scansStore.filters.search}
					onSearchChange={(q) => scansStore.setSearch(q)}
					statuses={scansStore.filters.statuses}
					statusCounts={scansStore.stats?.by_status}
					onToggleStatus={(s) => scansStore.toggleStatus(s)}
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
			{#if !targetId}
				<Button
					variant="outline"
					size="sm"
					class="h-9 gap-2 {grouped ? 'border-primary/50 bg-primary/5' : ''}"
					aria-pressed={grouped}
					onclick={() => scansStore.toggleGroupByTarget()}
				>
					<Layers class="h-4 w-4" />
					<span class="hidden sm:inline">Group by target</span>
				</Button>
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

		{#if activeChips.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b bg-muted/10">
				{#each activeChips as chip (chip.key)}
					<Badge variant="outline" class="gap-1 bg-background font-normal">
						{chip.label}
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
					</Badge>
				{/each}
				<button
					class="ml-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
					<Empty.Title>Couldn't load scans</Empty.Title>
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
					<Empty.Title>No scans match your filters</Empty.Title>
					<Empty.Description>Try widening the search or clearing filters.</Empty.Description>
				</Empty.Header>
				<Empty.Content>
					<Button
						size="sm"
						variant="outline"
						class="gap-2"
						onclick={() => scansStore.clearFilters()}
					>
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
						Launch a scan to start building scan history.
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

			<div class="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="text-xs text-muted-foreground">
						Showing {groups.length} of {pagination.totalItems} target{pagination.totalItems !== 1
							? 's'
							: ''}
					</div>
					<PageSizeSelector
						pageSize={pagination.pageSize}
						onPageSizeChange={(size) => scansStore.setPageSize(size)}
					/>
				</div>

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
			</div>
		{:else}
			<ScanListHeader
				{targetId}
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
						onRescan={(s) => onRescan?.(s)}
						onCancel={(s) => (cancelTarget = s)}
						onDelete={(s) => (deleteTarget = s)}
					/>
				{/each}
			</div>

			<div class="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="text-xs text-muted-foreground">
						Showing {scans.length} of {pagination.totalItems} scan{pagination.totalItems !== 1
							? 's'
							: ''}
					</div>
					<PageSizeSelector
						pageSize={pagination.pageSize}
						onPageSizeChange={(size) => scansStore.setPageSize(size)}
					/>
				</div>

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
			</div>
		{/if}
	</Card.Root>
</div>

<AlertDialog.Root open={!!cancelTarget} onOpenChange={(o) => !o && (cancelTarget = null)}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Cancel this scan?</AlertDialog.Title>
			<AlertDialog.Description>
				The scan will stop queuing further work and be marked cancelled.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Keep running</AlertDialog.Cancel>
			<AlertDialog.Action onclick={confirmCancel}>Cancel scan</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<AlertDialog.Root open={!!deleteTarget} onOpenChange={(o) => !o && (deleteTarget = null)}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Delete this scan?</AlertDialog.Title>
			<AlertDialog.Description>
				This removes the scan and all of its results. This cannot be undone.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Keep</AlertDialog.Cancel>
			<AlertDialog.Action
				class={buttonVariants({ variant: 'destructive' })}
				onclick={confirmDelete}
			>
				Delete
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
