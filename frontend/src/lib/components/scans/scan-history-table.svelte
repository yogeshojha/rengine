<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Search,
		X,
		Plus,
		RefreshCw,
		ListFilter,
		CalendarRange,
		ArrowDownUp,
		ArrowUp,
		ArrowDown,
		Ellipsis,
		Play,
		Ban,
		Trash2,
		History,
		TriangleAlert,
		ExternalLink
	} from 'lucide-svelte';
	import * as Table from '$lib/components/ui/table';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Pagination from '$lib/components/ui/pagination';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ScanInsights from './scan-insights.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		SCAN_STATUS_LABEL,
		scanStatusVariant,
		scanStatusIcon,
		isLiveStatus,
		durationLabel,
		scanCountPills,
		compareScans
	} from '$lib/utilities/scan-status';
	import { SCAN_STATUSES, SCAN_SORT_KEYS } from '$lib/types/scan';
	import type { ScanRead, ScanStats, ScanStatus, ScanSortKey } from '$lib/types/scan';

	interface Props {
		scans: ScanRead[];
		stats?: ScanStats | null;
		loading: boolean;
		refreshing?: boolean;
		error?: string | null;
		targetId?: string;
		showSummary?: boolean;
		onLaunch?: () => void;
		onRefresh?: () => void;
		onRescan: (scan: ScanRead) => void;
		onCancel: (scan: ScanRead) => Promise<void> | void;
		onDelete: (scan: ScanRead) => Promise<void> | void;
		onRetry?: () => void;
	}

	let {
		scans,
		stats = null,
		loading,
		refreshing = false,
		error = null,
		targetId,
		showSummary = false,
		onLaunch,
		onRefresh,
		onRescan,
		onCancel,
		onDelete,
		onRetry
	}: Props = $props();

	const PER_PAGE = 20;

	const TIME_RANGES = [
		{ key: 'all', label: 'All time' },
		{ key: '24h', label: 'Last 24 hours' },
		{ key: '7d', label: 'Last 7 days' },
		{ key: '30d', label: 'Last 30 days' }
	] as const;
	type TimeRange = (typeof TIME_RANGES)[number]['key'];
	const RANGE_MS: Record<TimeRange, number> = {
		all: 0,
		'24h': 86_400_000,
		'7d': 604_800_000,
		'30d': 2_592_000_000
	};

	const SORT_LABELS: Record<ScanSortKey, string> = {
		started: 'Started',
		duration: 'Duration',
		status: 'Status',
		subdomains: 'Subdomains',
		vulnerabilities: 'Vulnerabilities'
	};

	let search = $state('');
	let statusFilter = $state<ScanStatus[]>([]);
	let engineFilter = $state<string[]>([]);
	let contextFilter = $state<string[]>([]);
	let timeRange = $state<TimeRange>('all');
	let sortKey = $state<ScanSortKey>('started');
	let sortDir = $state<'asc' | 'desc'>('desc');
	let page = $state(1);
	let now = $state(Date.now());

	let cancelTarget = $state<ScanRead | null>(null);
	let deleteTarget = $state<ScanRead | null>(null);

	let engines = $derived([...new Set(scans.map((s) => s.engine_name))].sort());
	let contexts = $derived(
		[...new Set(scans.map((s) => s.context_name).filter((c): c is string => !!c))].sort()
	);

	let statusCounts = $derived.by(() => {
		const m = Object.fromEntries(SCAN_STATUSES.map((s) => [s, 0])) as Record<ScanStatus, number>;
		for (const s of scans) m[s.status] += 1;
		return m;
	});
	let engineCounts = $derived.by(() => {
		const m: Record<string, number> = {};
		for (const s of scans) m[s.engine_name] = (m[s.engine_name] ?? 0) + 1;
		return m;
	});
	let contextCounts = $derived.by(() => {
		const m: Record<string, number> = {};
		for (const s of scans) if (s.context_name) m[s.context_name] = (m[s.context_name] ?? 0) + 1;
		return m;
	});

	let hasActiveFilters = $derived(
		search.trim().length > 0 ||
			statusFilter.length > 0 ||
			engineFilter.length > 0 ||
			contextFilter.length > 0 ||
			timeRange !== 'all'
	);

	let filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		const cutoff = RANGE_MS[timeRange] ? Date.now() - RANGE_MS[timeRange] : 0;
		return scans.filter((s) => {
			if (statusFilter.length && !statusFilter.includes(s.status)) return false;
			if (engineFilter.length && !engineFilter.includes(s.engine_name)) return false;
			if (contextFilter.length && !contextFilter.includes(s.context_name ?? '')) return false;
			if (cutoff && new Date(s.started_at ?? s.created_at).getTime() < cutoff) return false;
			if (q) {
				const hay = `${s.execution_config.target_value} ${s.engine_name} ${s.context_name ?? ''}`;
				if (!hay.toLowerCase().includes(q)) return false;
			}
			return true;
		});
	});

	let sorted = $derived.by(() => {
		const dir = sortDir === 'asc' ? 1 : -1;
		const t = sortKey === 'duration' ? now : Date.now();
		return [...filtered].sort((a, b) => compareScans(a, b, sortKey, t) * dir);
	});

	let totalPages = $derived(Math.max(1, Math.ceil(sorted.length / PER_PAGE)));
	$effect(() => {
		if (page > totalPages) page = totalPages;
	});
	let pageRows = $derived(sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE));

	let hasLiveOnPage = $derived(pageRows.some((s) => isLiveStatus(s.status)));
	$effect(() => {
		if (!hasLiveOnPage) return;
		const t = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(t);
	});

	let truncated = $derived(stats != null && stats.total > scans.length);

	function toggle<T>(list: T[], value: T): T[] {
		return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
	}

	function sortBy(key: ScanSortKey) {
		if (sortKey === key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		else {
			sortKey = key;
			sortDir = 'desc';
		}
	}

	function clearFilters() {
		search = '';
		statusFilter = [];
		engineFilter = [];
		contextFilter = [];
		timeRange = 'all';
	}

	function open(scan: ScanRead) {
		goto(`/scans/${scan.id}`);
	}

	function onCardKeydown(e: KeyboardEvent, scan: ScanRead) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			open(scan);
		}
	}

	async function confirmCancel() {
		const s = cancelTarget;
		cancelTarget = null;
		if (s) await onCancel(s);
	}

	async function confirmDelete() {
		const s = deleteTarget;
		deleteTarget = null;
		if (s) await onDelete(s);
	}
</script>

{#snippet sortHead(key: ScanSortKey, label: string, right = false)}
	<Table.Head
		class={right ? 'text-right' : ''}
		aria-sort={sortKey === key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
	>
		<button
			type="button"
			class="inline-flex items-center gap-1 hover:text-foreground {right
				? 'flex-row-reverse'
				: ''}"
			aria-label="Sort by {label}{sortKey === key
				? sortDir === 'asc'
					? ', ascending'
					: ', descending'
				: ''}"
			onclick={() => sortBy(key)}
		>
			{label}
			{#if sortKey === key}
				{#if sortDir === 'asc'}<ArrowUp class="h-3 w-3" />{:else}<ArrowDown class="h-3 w-3" />{/if}
			{/if}
		</button>
	</Table.Head>
{/snippet}

{#snippet statusCell(scan: ScanRead)}
	{@const StatusIcon = scanStatusIcon(scan.status)}
	<Badge variant={scanStatusVariant(scan.status)} class="gap-1 font-normal">
		<StatusIcon class="h-3 w-3 {scan.status === 'running' ? 'animate-spin' : ''}" />
		{SCAN_STATUS_LABEL[scan.status]}
	</Badge>
{/snippet}

{#snippet resultCell(scan: ScanRead)}
	{#if isLiveStatus(scan.status)}
		<span class="text-xs text-muted-foreground">
			{scan.subdomains_found} subs · scanning…
		</span>
	{:else}
		<div class="flex flex-wrap gap-1">
			{#each scanCountPills(scan) as pill (pill.key)}
				{@const PillIcon = pill.icon}
				<Badge
					variant="outline"
					title={pill.label}
					class="gap-1 font-normal tabular-nums {pill.emphasis
						? 'text-destructive border-destructive/40'
						: 'text-muted-foreground'}"
				>
					<PillIcon class="h-3 w-3" />
					{pill.value}
				</Badge>
			{/each}
		</div>
	{/if}
{/snippet}

{#snippet rowActions(scan: ScanRead)}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="ghost"
					size="icon-sm"
					class="h-7 w-7"
					aria-label="Actions for {scan.execution_config.target_value}"
				>
					<Ellipsis class="h-4 w-4" />
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end">
			<DropdownMenu.Item onSelect={() => open(scan)}>
				<ExternalLink class="mr-2 h-3.5 w-3.5" /> Open
			</DropdownMenu.Item>
			<DropdownMenu.Item onSelect={() => onRescan(scan)}>
				<Play class="mr-2 h-3.5 w-3.5" /> Re-scan
			</DropdownMenu.Item>
			<DropdownMenu.Separator />
			{#if isLiveStatus(scan.status)}
				<DropdownMenu.Item onSelect={() => (cancelTarget = scan)}>
					<Ban class="mr-2 h-3.5 w-3.5" /> Cancel
				</DropdownMenu.Item>
			{:else}
				<DropdownMenu.Item class="text-destructive" onSelect={() => (deleteTarget = scan)}>
					<Trash2 class="mr-2 h-3.5 w-3.5" /> Delete
				</DropdownMenu.Item>
			{/if}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/snippet}

<div class="space-y-3">
	{#if showSummary && !loading && !error}
		<ScanInsights {stats} onFilterStatus={(s) => (statusFilter = s)} />
	{/if}

	<div class="flex flex-wrap items-center gap-2">
		<div class="relative min-w-[180px] flex-1">
			<Search
				class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={search}
				placeholder="Search target, engine, context…"
				class="h-8 pl-8 text-sm"
			/>
			{#if search}
				<button
					type="button"
					class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
					aria-label="Clear search"
					onclick={() => (search = '')}
				>
					<X class="h-3.5 w-3.5" />
				</button>
			{/if}
		</div>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="outline" size="sm" class="h-8 gap-1.5 text-xs">
						<ListFilter class="h-3.5 w-3.5" /> Status
						{#if statusFilter.length}<Badge variant="secondary" class="ml-1"
								>{statusFilter.length}</Badge
							>{/if}
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start">
				{#each SCAN_STATUSES as s (s)}
					<DropdownMenu.CheckboxItem
						checked={statusFilter.includes(s)}
						onCheckedChange={() => (statusFilter = toggle(statusFilter, s))}
					>
						<span class="flex-1">{SCAN_STATUS_LABEL[s]}</span>
						<span class="ml-3 tabular-nums text-muted-foreground">{statusCounts[s]}</span>
					</DropdownMenu.CheckboxItem>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		{#if engines.length > 0}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-8 gap-1.5 text-xs"
							disabled={engines.length < 2}
							title={engines.length < 2 ? 'Only one engine in use' : undefined}
						>
							<ListFilter class="h-3.5 w-3.5" /> Engine
							{#if engineFilter.length}<Badge variant="secondary" class="ml-1"
									>{engineFilter.length}</Badge
								>{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-72 overflow-y-auto">
					{#each engines as e (e)}
						<DropdownMenu.CheckboxItem
							checked={engineFilter.includes(e)}
							onCheckedChange={() => (engineFilter = toggle(engineFilter, e))}
						>
							<span class="flex-1 truncate">{e}</span>
							<span class="ml-3 tabular-nums text-muted-foreground">{engineCounts[e]}</span>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		{#if contexts.length > 0}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-8 gap-1.5 text-xs">
							<ListFilter class="h-3.5 w-3.5" /> Context
							{#if contextFilter.length}<Badge variant="secondary" class="ml-1"
									>{contextFilter.length}</Badge
								>{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-72 overflow-y-auto">
					{#each contexts as c (c)}
						<DropdownMenu.CheckboxItem
							checked={contextFilter.includes(c)}
							onCheckedChange={() => (contextFilter = toggle(contextFilter, c))}
						>
							<span class="flex-1 truncate">{c}</span>
							<span class="ml-3 tabular-nums text-muted-foreground">{contextCounts[c]}</span>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="outline" size="sm" class="h-8 gap-1.5 text-xs">
						<CalendarRange class="h-3.5 w-3.5" />
						{TIME_RANGES.find((r) => r.key === timeRange)?.label}
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start">
				{#each TIME_RANGES as r (r.key)}
					<DropdownMenu.CheckboxItem
						checked={timeRange === r.key}
						onCheckedChange={() => (timeRange = r.key)}
					>
						{r.label}
					</DropdownMenu.CheckboxItem>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="outline" size="sm" class="h-8 gap-1.5 text-xs">
						<ArrowDownUp class="h-3.5 w-3.5" /> {SORT_LABELS[sortKey]}
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start">
				{#each SCAN_SORT_KEYS as key (key)}
					<DropdownMenu.CheckboxItem checked={sortKey === key} onCheckedChange={() => sortBy(key)}>
						{SORT_LABELS[key]}
					</DropdownMenu.CheckboxItem>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>

		{#if hasActiveFilters}
			<Button variant="ghost" size="sm" class="h-8 gap-1 text-xs" onclick={clearFilters}>
				<X class="h-3.5 w-3.5" /> Clear
			</Button>
		{/if}

		<div class="ml-auto flex items-center gap-2">
			{#if hasActiveFilters && !loading}
				<span class="text-xs text-muted-foreground tabular-nums">
					{sorted.length} of {scans.length}
				</span>
			{/if}
			{#if onRefresh}
				<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={onRefresh}>
					<RefreshCw class="h-3.5 w-3.5 {refreshing ? 'animate-spin' : ''}" /> Refresh
				</Button>
			{/if}
			{#if onLaunch}
				<Button size="sm" class="h-8 gap-1.5 text-xs" onclick={onLaunch}>
					<Plus class="h-3.5 w-3.5" /> New scan
				</Button>
			{/if}
		</div>
	</div>

	{#if truncated && !loading}
		<p
			class="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-600 dark:text-amber-500"
		>
			Showing the {scans.length} most recent of {stats?.total} scans — narrow with filters to find older runs.
		</p>
	{/if}

	{#if loading && scans.length === 0}
		<div class="rounded-lg border border-border">
			<Table.Root>
				<Table.Body>
					{#each Array(6) as _, i (i)}
						<Table.Row
							><Table.Cell class="py-3"><Skeleton class="h-5 w-full" /></Table.Cell></Table.Row
						>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>
	{:else if error}
		<Empty.Root class="rounded-lg border border-dashed py-16">
			<Empty.Header>
				<Empty.Media variant="icon" class="bg-destructive/10 text-destructive">
					<TriangleAlert />
				</Empty.Media>
				<Empty.Title class="text-sm">Couldn't load scans</Empty.Title>
				<Empty.Description>{error}</Empty.Description>
			</Empty.Header>
			{#if onRetry}
				<Empty.Content>
					<Button size="sm" variant="outline" class="gap-1.5" onclick={onRetry}>
						<RefreshCw class="h-3.5 w-3.5" /> Retry
					</Button>
				</Empty.Content>
			{/if}
		</Empty.Root>
	{:else if scans.length === 0}
		<Empty.Root class="rounded-lg border border-dashed bg-card/40 py-16">
			<Empty.Header>
				<Empty.Media
					variant="icon"
					class="h-14 w-14 rounded-2xl bg-muted text-muted-foreground/60 [&_svg:not([class*='size-'])]:size-6"
				>
					<History />
				</Empty.Media>
				<Empty.Title class="text-sm">No scans yet</Empty.Title>
				<Empty.Description class="max-w-sm">
					Launch a scan to start building scan history.
				</Empty.Description>
			</Empty.Header>
			{#if onLaunch}
				<Empty.Content>
					<Button size="sm" class="gap-2" onclick={onLaunch}>
						<Plus class="h-3.5 w-3.5" /> New scan
					</Button>
				</Empty.Content>
			{/if}
		</Empty.Root>
	{:else if sorted.length === 0}
		<Empty.Root class="rounded-lg border border-dashed py-16">
			<Empty.Header>
				<Empty.Title class="text-sm">No scans match your filters</Empty.Title>
				<Empty.Description>Try widening the search or clearing filters.</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" class="gap-1.5" onclick={clearFilters}>
					<X class="h-3.5 w-3.5" /> Clear filters
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<div class="hidden rounded-lg border border-border sm:block">
			<Table.Root>
				<Table.Header>
					<Table.Row>
						{#if !targetId}<Table.Head>Target</Table.Head>{/if}
						{@render sortHead('status', 'Status')}
						<Table.Head>Engine</Table.Head>
						{@render sortHead('subdomains', 'Results')}
						{@render sortHead('duration', 'Duration', true)}
						{@render sortHead('started', 'Started', true)}
						<Table.Head class="w-10"></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each pageRows as scan (scan.id)}
						<Table.Row class="cursor-pointer hover:bg-muted/50" onclick={() => open(scan)}>
							{#if !targetId}
								<Table.Cell class="font-mono text-xs"
									>{scan.execution_config.target_value}</Table.Cell
								>
							{/if}
							<Table.Cell>{@render statusCell(scan)}</Table.Cell>
							<Table.Cell class="text-sm">{scan.engine_name}</Table.Cell>
							<Table.Cell>{@render resultCell(scan)}</Table.Cell>
							<Table.Cell class="text-right text-xs text-muted-foreground tabular-nums">
								{durationLabel(scan, now)}
							</Table.Cell>
							<Table.Cell class="text-right text-xs text-muted-foreground">
								{relativeTime(scan.started_at ?? scan.created_at)}
							</Table.Cell>
							<Table.Cell class="text-right" onclick={(e) => e.stopPropagation()}>
								<div class="flex items-center justify-end gap-0.5">
									{#if isLiveStatus(scan.status)}
										<Button
											variant="ghost"
											size="icon-sm"
											class="h-7 w-7 text-muted-foreground hover:text-destructive"
											aria-label="Cancel scan for {scan.execution_config.target_value}"
											onclick={() => (cancelTarget = scan)}
										>
											<Ban class="h-3.5 w-3.5" />
										</Button>
									{/if}
									{@render rowActions(scan)}
								</div>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>

		<div class="space-y-2 sm:hidden">
			{#each pageRows as scan (scan.id)}
				<div
					class="space-y-2 rounded-lg border border-border p-3"
					role="button"
					tabindex="0"
					aria-label="Open scan for {scan.execution_config.target_value}"
					onclick={() => open(scan)}
					onkeydown={(e) => onCardKeydown(e, scan)}
				>
					<div class="flex items-center justify-between gap-2">
						{#if !targetId}
							<span class="truncate font-mono text-xs">{scan.execution_config.target_value}</span>
						{:else}
							<span class="text-sm font-medium">{scan.engine_name}</span>
						{/if}
						{@render statusCell(scan)}
					</div>
					<div class="text-xs text-muted-foreground">
						{#if !targetId}{scan.engine_name} ·
						{/if}{relativeTime(scan.started_at ?? scan.created_at)} ·
						{durationLabel(scan, now)}
					</div>
					{@render resultCell(scan)}
				</div>
			{/each}
		</div>

		{#if totalPages > 1}
			<Pagination.Root count={sorted.length} perPage={PER_PAGE} bind:page>
				{#snippet children({ pages, currentPage })}
					<Pagination.Content>
						<Pagination.Item><Pagination.Previous /></Pagination.Item>
						{#each pages as p (p.key)}
							{#if p.type === 'ellipsis'}
								<Pagination.Item><Pagination.Ellipsis /></Pagination.Item>
							{:else}
								<Pagination.Item>
									<Pagination.Link page={p} isActive={currentPage === p.value}
										>{p.value}</Pagination.Link
									>
								</Pagination.Item>
							{/if}
						{/each}
						<Pagination.Item><Pagination.Next /></Pagination.Item>
					</Pagination.Content>
				{/snippet}
			</Pagination.Root>
		{/if}
	{/if}
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
