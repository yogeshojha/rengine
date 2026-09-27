<script lang="ts">
	import { untrack, tick } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import Ban from '@lucide/svelte/icons/ban';
	import Search from '@lucide/svelte/icons/search';
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Keyboard from '@lucide/svelte/icons/keyboard';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import History from '@lucide/svelte/icons/history';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';

	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import * as Empty from '$lib/components/ui/empty';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Kbd } from '$lib/components/ui/kbd';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import PageSizeSelector from '$lib/components/targets/page-size-selector.svelte';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		SCAN_STATUS_TABS,
		SCAN_POLL_MS,
		isOpenStatus,
		scanStatusTab
	} from '$lib/utilities/scan-status';
	import { quote, withToken, withoutToken, hasToken } from '$lib/utilities/scan-query';
	import { eligibility } from '$lib/utilities/compare';
	import { formatShortDate } from '$lib/utilities/dates';
	import { ROUTES } from '$lib/config/routes';
	import { SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import type { ScanRead, ScanSortKey } from '$lib/types/scan';

	import ScanStatusTabs from './scan-status-tabs.svelte';
	import ScanBulkActionBar from './scan-bulk-action-bar.svelte';
	import ScanRow from './history/scan-row.svelte';
	import HistoryChart from './history/history-chart.svelte';
	import CompareSheet from './history/compare-sheet.svelte';
	import { COL } from './history/columns';
	import { SEV_CHIP, forgetFindings } from './history/findings';
	import {
		BRIEF_TABS,
		HISTORY_COLUMNS,
		HISTORY_COLUMN_LABELS,
		STRIP_SEVERITIES,
		historyPrefs
	} from './history/prefs.svelte';

	interface Props {
		targetId?: string;
		onLaunch?: () => void;
		onRescan?: (scan: ScanRead) => void;
		onRescanMany?: (targetIds: string[]) => void;
	}

	let { targetId, onLaunch, onRescan, onRescanMany }: Props = $props();

	const SAVED_VIEWS = [
		{ label: 'Critical findings', token: 'severity:critical' },
		{ label: 'Failed', token: 'status:failed' },
		{ label: 'Added web assets', token: 'is:added' },
		{ label: 'Partial coverage', token: 'is:partial' }
	];

	let cancelTarget = $state<ScanRead | null>(null);
	let deleteTarget = $state<ScanRead | null>(null);
	let bulkDeleteOpen = $state(false);
	let bulkCancelOpen = $state(false);
	let cancelAllOpen = $state(false);
	let cancellingAll = $state(false);
	let shortcutsOpen = $state(false);
	let now = $state(Date.now());
	let searchEl = $state<HTMLInputElement | null>(null);
	let queryText = $state(scansStore.filters.query);
	let compare = $state<{ current: string; baseline: string | null } | null>(null);

	let expanded = new SvelteSet<string>();
	let earlier = $state<Record<string, ScanRead[] | 'loading'>>({});
	let focusId = $state<string | null>(null);
	let flashId = $state<string | null>(null);
	const selected = new SvelteSet<string>();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');

	$effect(() => {
		const project = projectsStore.activeProject;
		const tid = targetId;
		if (project && projectsStore.hasFetched) {
			untrack(() => {
				scansStore.init(project.id, tid);
				queryText = scansStore.filters.query;
			});
		}
	});

	$effect(() => {
		const t = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(t);
	});

	$effect(() => {
		if (!scansStore.hasLive) return;
		engineCatalogStore.fetch();
		const poll = setInterval(() => scansStore.refresh(), SCAN_POLL_MS);
		return () => clearInterval(poll);
	});

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => scansStore.refresh());
	});

	let scans = $derived(scansStore.scans);
	let latest = $derived(scansStore.filters.latest && !targetId);
	let pagination = $derived(scansStore.pagination);
	let statusTab = $derived(scanStatusTab(scansStore.filters.statuses));
	let parseError = $derived(scansStore.parsed.error);
	let days = $derived(scansStore.days);
	let windowRuns = $derived(days.reduce((n, d) => n + d.runs, 0));
	let byStatus = $derived(scansStore.stats?.by_status);
	let openCount = $derived(byStatus ? byStatus.running + byStatus.pending + byStatus.paused : 0);
	let canCancelAll = $derived(openCount > 0 || scansStore.hasLive);
	let sevRuns = $derived(
		STRIP_SEVERITIES.map((s) => ({
			sev: s,
			n: days.reduce((a, d) => a + (d[s as 'critical' | 'high' | 'medium'] ?? 0), 0),
			active: hasToken(scansStore.filters.query, `severity:${s}`)
		}))
	);

	let visible = $derived.by(() => {
		const out: { scan: ScanRead; nested: boolean }[] = [];
		for (const s of scans) {
			out.push({ scan: s, nested: false });
			const kids = earlier[s.id];
			if (Array.isArray(kids)) for (const k of kids) out.push({ scan: k, nested: true });
		}
		return out;
	});
	let allRows = $derived(visible.map((v) => v.scan));
	let selectedScans = $derived(allRows.filter((s) => selected.has(s.id)));
	let selectedLive = $derived(selectedScans.filter((s) => isOpenStatus(s.status)).length);
	let selectedTargets = $derived([...new Set(selectedScans.map((s) => s.target_id))]);
	let pair = $derived(eligibility(selectedScans));
	let compareHref = $derived(
		pair.ok && pair.current && pair.baseline
			? ROUTES.compare(pair.current.id, pair.baseline.id)
			: null
	);
	let selectAll = $derived<boolean | 'indeterminate'>(
		scans.length > 0 && scans.every((s) => selected.has(s.id))
			? true
			: selectedScans.length > 0
				? 'indeterminate'
				: false
	);

	$effect(() => {
		const ids = new Set(allRows.map((s) => s.id));
		for (const id of selected) if (!ids.has(id)) selected.delete(id);
	});

	function setQuery(q: string, immediate = false) {
		queryText = q;
		scansStore.setQuery(q, immediate);
	}

	function toggleToken(token: string) {
		setQuery(
			hasToken(queryText, token) ? withoutToken(queryText, token) : withToken(queryText, token),
			true
		);
	}

	function toggleSeverity(sev: string) {
		const token = `severity:${sev}`;
		if (!hasToken(queryText, token)) {
			scansStore.filters.latest = false;
			if (days.length && !scansStore.filters.startedFrom)
				scansStore.filters.startedFrom = new Date(days[0].day).toISOString();
		}
		toggleToken(token);
	}

	function toggleSelectAll() {
		if (scans.every((s) => selected.has(s.id))) selected.clear();
		else for (const s of scans) selected.add(s.id);
	}

	function toggleExpand(id: string) {
		if (expanded.has(id)) expanded.delete(id);
		else expanded.add(id);
	}

	async function toggleEarlier(scan: ScanRead) {
		if (earlier[scan.id]) {
			const next = { ...earlier };
			delete next[scan.id];
			earlier = next;
			return;
		}
		earlier = { ...earlier, [scan.id]: 'loading' };
		try {
			const rows = await scansStore.loadTargetScans(scan.target_id, scan.id);
			earlier = { ...earlier, [scan.id]: rows };
		} catch {
			const next = { ...earlier };
			delete next[scan.id];
			earlier = next;
			toast.error('Earlier runs not loaded');
		}
	}

	async function jump(scanId: string) {
		if (!allRows.some((s) => s.id === scanId)) {
			goto(ROUTES.scan(scanId));
			return;
		}
		expanded.add(scanId);
		focusId = scanId;
		flashId = scanId;
		await tick();
		document
			.getElementById(`scan-row-${scanId}`)
			?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		setTimeout(() => (flashId = null), 1200);
	}

	function sortBy(key: ScanSortKey) {
		scansStore.setSort(key);
	}

	function changed() {
		for (const s of scans) forgetFindings(s.id);
		scansStore.refresh();
	}

	async function pause(scan: ScanRead) {
		if (await scansStore.pause(scan)) toast.success('Scan paused');
		else toast.error(scansStore.error ?? 'Scan not paused');
	}

	async function resume(scan: ScanRead) {
		if (await scansStore.resume(scan)) toast.success('Scan resumed');
		else toast.error(scansStore.error ?? 'Scan not resumed');
	}

	async function confirmCancel() {
		const s = cancelTarget;
		cancelTarget = null;
		if (s && (await scansStore.cancel(s))) toast.success('Scan cancelled');
		else if (s) toast.error(scansStore.error ?? 'Scan not cancelled');
	}

	async function confirmDelete() {
		const s = deleteTarget;
		deleteTarget = null;
		if (s && (await scansStore.remove(s))) toast.success('Scan deleted');
		else if (s) toast.error(scansStore.error ?? 'Scan not deleted');
	}

	async function confirmBulkDelete() {
		const ids = [...selected];
		bulkDeleteOpen = false;
		if (!ids.length) return;
		const { ok, failed } = await scansStore.removeMany(ids);
		selected.clear();
		if (ok) toast.success(`Deleted ${ok} scan${ok !== 1 ? 's' : ''}`);
		if (failed) toast.error(`${failed} scan${failed !== 1 ? 's' : ''} not deleted`);
	}

	async function confirmBulkCancel() {
		const ids = selectedScans.filter((s) => isOpenStatus(s.status)).map((s) => s.id);
		bulkCancelOpen = false;
		if (!ids.length) return;
		const { ok, failed } = await scansStore.cancelMany(ids);
		if (ok) toast.success(`Cancelled ${ok} scan${ok !== 1 ? 's' : ''}`);
		if (failed) toast.error(`${failed} scan${failed !== 1 ? 's' : ''} not cancelled`);
	}

	async function confirmCancelAll() {
		cancelAllOpen = false;
		cancellingAll = true;
		const n = await scansStore.cancelAll();
		cancellingAll = false;
		if (n === null) toast.error(scansStore.error ?? 'Scans not cancelled');
		else toast.success(`Cancelled ${n} scan${n !== 1 ? 's' : ''}`);
	}

	function openCompare(scan?: ScanRead) {
		if (scan) {
			compare = { current: scan.id, baseline: null };
			return;
		}
		if (pair.ok && pair.current && pair.baseline)
			compare = { current: pair.current.id, baseline: pair.baseline.id };
		else if (pair.reason) toast.error(pair.reason);
	}

	function typing(e: KeyboardEvent): boolean {
		const el = e.target as HTMLElement | null;
		return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
	}

	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === '/' && !typing(e)) {
			e.preventDefault();
			searchEl?.focus();
			return;
		}
		if (typing(e) || document.querySelector('[role=dialog],[role=menu]')) return;
		const idx = visible.findIndex((v) => v.scan.id === focusId);
		const focused = idx >= 0 ? visible[idx].scan : null;
		const move = (d: number) => {
			const next = visible[Math.max(0, Math.min(visible.length - 1, (idx < 0 ? -1 : idx) + d))];
			if (!next) return;
			focusId = next.scan.id;
			document.getElementById(`scan-row-${focusId}`)?.scrollIntoView({ block: 'nearest' });
		};
		switch (e.key) {
			case 'j':
			case 'ArrowDown':
				e.preventDefault();
				move(1);
				break;
			case 'k':
			case 'ArrowUp':
				e.preventDefault();
				move(-1);
				break;
			case 'o':
				if (focused) toggleExpand(focused.id);
				break;
			case 'x':
				if (focused) {
					if (selected.has(focused.id)) selected.delete(focused.id);
					else selected.add(focused.id);
				}
				break;
			case 'Enter':
				if (focused) goto(ROUTES.scan(focused.id));
				break;
			case 'c':
				if (selectedScans.length === 2) openCompare();
				else if (focused && !focused.is_first_scan) openCompare(focused);
				break;
			case '?':
				shortcutsOpen = true;
				break;
			case 'Escape':
				if (focused && expanded.has(focused.id)) expanded.delete(focused.id);
				else if (selected.size) selected.clear();
				break;
			default:
				if (/^[1-4]$/.test(e.key) && focused && expanded.has(focused.id))
					historyPrefs.tab = BRIEF_TABS[Number(e.key) - 1];
		}
	}

	const SHORTCUTS: [string, string][] = [
		['j / k', 'Move between runs'],
		['o', 'Expand or collapse the run brief'],
		['1 to 4', 'Switch brief tab'],
		['Enter', 'Open results'],
		['x', 'Select run'],
		['c', 'Compare runs'],
		['/', 'Search'],
		['Esc', 'Collapse or clear selection']
	];
</script>

<svelte:window onkeydown={onKey} />

{#snippet sortHead(label: string, key: ScanSortKey, cls: string)}
	<button
		type="button"
		class="{cls} items-center gap-1 text-left tracking-wide uppercase hover:text-foreground {scansStore
			.filters.sortKey === key
			? 'text-foreground'
			: ''}"
		onclick={() => sortBy(key)}
	>
		{label}
		{#if scansStore.filters.sortKey === key}
			{#if scansStore.filters.sortDir === 'desc'}<ArrowDown class="size-3" />{:else}<ArrowUp
					class="size-3"
				/>{/if}
		{/if}
	</button>
{/snippet}

<Card.Root class="gap-0 overflow-hidden py-0">
	<!-- strip -->
	<div class="grid gap-x-8 gap-y-4 border-b px-4 py-4 lg:grid-cols-[auto_minmax(0,1fr)]">
		<div class="flex flex-wrap items-start gap-x-8 gap-y-3">
			<div class="flex flex-col gap-0.5">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase">Runs · 30 days</span>
				<span class="font-mono text-2xl font-semibold tabular-nums"
					>{windowRuns.toLocaleString()}</span
				>
			</div>
			<div class="flex flex-col gap-0.5">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase">Running now</span>
				<span class="flex items-center gap-2 font-mono text-2xl font-semibold tabular-nums">
					{byStatus?.running ?? 0}
					{#if (byStatus?.running ?? 0) > 0}
						<span class="size-2 rounded-full bg-info"></span>
					{/if}
				</span>
				<span class="text-2xs text-muted-foreground">
					{byStatus?.pending ?? 0} queued · {byStatus?.paused ?? 0} paused
				</span>
			</div>
			<div class="flex flex-col gap-1">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase"
					>Runs with findings · 30 days</span
				>
				<div class="flex items-center gap-1.5">
					{#each sevRuns as s (s.sev)}
						<button
							type="button"
							class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 font-mono text-sm font-semibold tabular-nums transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {SEV_CHIP[
								s.sev
							].chip} {s.active ? 'ring-2 ring-current/50' : ''} {s.n ? '' : 'opacity-50'}"
							aria-pressed={s.active}
							aria-label="Runs with {SEVERITY_LABELS[s.sev].toLowerCase()} findings: {s.n}"
							onclick={() => toggleSeverity(s.sev)}
						>
							<span class="text-2xs font-medium opacity-70">{SEVERITY_LABELS[s.sev]}</span>
							{s.n}
						</button>
					{/each}
				</div>
			</div>
		</div>
		<HistoryChart
			{days}
			from={scansStore.filters.startedFrom}
			to={scansStore.filters.startedTo}
			onRange={(f, t) => scansStore.setRange(f, t)}
		/>
	</div>

	<!-- tabs -->
	<div class="flex flex-wrap items-center justify-between gap-2 border-b px-2">
		<ScanStatusTabs
			active={statusTab}
			counts={scansStore.stats?.by_status ?? null}
			total={scansStore.stats?.total ?? 0}
			onChange={(tab) =>
				scansStore.setStatuses(SCAN_STATUS_TABS.find((t) => t.key === tab)?.statuses ?? [])}
		/>
		{#if !targetId}
			<ToggleGroup.Root
				type="single"
				variant="outline"
				size="sm"
				value={latest ? 'latest' : 'all'}
				onValueChange={(v) => v && scansStore.setLatest(v === 'latest')}
				aria-label="View"
				class="my-1.5"
			>
				<ToggleGroup.Item value="all" class="px-3 text-xs">All runs</ToggleGroup.Item>
				<ToggleGroup.Item value="latest" class="px-3 text-xs">Latest per target</ToggleGroup.Item>
			</ToggleGroup.Root>
		{/if}
	</div>

	<!-- filters -->
	<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
		<div class="flex min-w-[240px] flex-1 flex-col gap-1">
			<div
				class="flex h-9 items-center gap-2 rounded-md border bg-background px-2.5 focus-within:ring-2 focus-within:ring-ring/50 {parseError
					? 'border-destructive'
					: ''}"
			>
				<Search class="size-4 shrink-0 text-muted-foreground" />
				<input
					bind:this={searchEl}
					id="scan-history-search"
					class="h-full min-w-0 flex-1 bg-transparent font-mono text-sm outline-none placeholder:font-sans placeholder:text-muted-foreground"
					placeholder="target:acme severity:critical status:failed is:added"
					value={queryText}
					oninput={(e) => setQuery(e.currentTarget.value)}
					onkeydown={(e) => {
						if (e.key === 'Enter') setQuery(queryText, true);
						if (e.key === 'Escape') e.currentTarget.blur();
					}}
					aria-label="Search runs"
					aria-invalid={!!parseError}
					aria-describedby={parseError ? 'scan-history-search-error' : undefined}
				/>
				{#if queryText}
					<button
						type="button"
						class="rounded text-muted-foreground hover:text-foreground"
						aria-label="Clear search"
						onclick={() => setQuery('', true)}><X class="size-3.5" /></button
					>
				{:else}
					<Kbd class="hidden sm:inline-flex">/</Kbd>
				{/if}
			</div>
			{#if parseError}
				<p id="scan-history-search-error" class="text-2xs text-destructive">{parseError}</p>
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-2">
			{#if scansStore.stats?.engines?.length}
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button {...props} variant="outline" class="h-9">Engine</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-56">
						{#each scansStore.stats.engines as e (e.name)}
							{@const token = `engine:${quote(e.name)}`}
							<DropdownMenu.CheckboxItem
								checked={hasToken(queryText, token)}
								onCheckedChange={() => toggleToken(token)}
							>
								<span class="flex-1 truncate">{e.name}</span>
								<span class="font-mono text-2xs text-muted-foreground">{e.count}</span>
							</DropdownMenu.CheckboxItem>
						{/each}
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			{/if}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="icon"
							class="size-9"
							aria-label="Columns and density"
						>
							<Columns3 class="size-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-48">
					<DropdownMenu.Label>Columns</DropdownMenu.Label>
					{#each HISTORY_COLUMNS as c (c)}
						<DropdownMenu.CheckboxItem
							checked={historyPrefs.shows(c)}
							onCheckedChange={() => historyPrefs.toggle(c)}
						>
							{HISTORY_COLUMN_LABELS[c]}
						</DropdownMenu.CheckboxItem>
					{/each}
					<DropdownMenu.Separator />
					<DropdownMenu.Label>Density</DropdownMenu.Label>
					<DropdownMenu.RadioGroup
						value={historyPrefs.density}
						onValueChange={(v) =>
							(historyPrefs.density = v === 'compact' ? 'compact' : 'comfortable')}
					>
						<DropdownMenu.RadioItem value="comfortable">Comfortable</DropdownMenu.RadioItem>
						<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
					</DropdownMenu.RadioGroup>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
			<Hint text="Refresh">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon"
						class="size-9"
						aria-label="Refresh"
						onclick={() => scansStore.refresh()}
					>
						<RefreshCw class="size-4 {scansStore.refreshing ? 'animate-spin' : ''}" />
					</Button>
				{/snippet}
			</Hint>
			<Hint text="Keyboard shortcuts">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon"
						class="hidden size-9 sm:inline-flex"
						aria-label="Keyboard shortcuts"
						onclick={() => (shortcutsOpen = true)}
					>
						<Keyboard class="size-4" />
					</Button>
				{/snippet}
			</Hint>
			<Hint text={canCancelAll ? null : 'No unfinished scans.'}>
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<LoadingButton
							variant="outline"
							class="h-9 gap-2"
							disabled={!canCancelAll}
							loading={cancellingAll}
							loadingLabel="Cancelling"
							onclick={() => (cancelAllOpen = true)}
						>
							<Ban class="size-4" /> Cancel all
						</LoadingButton>
					</span>
				{/snippet}
			</Hint>
			{#if onLaunch}
				<Button class="h-9 gap-2" onclick={onLaunch}><Plus class="size-4" /> New scan</Button>
			{/if}
		</div>
	</div>

	<!-- saved views and active filters -->
	<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
		{#each SAVED_VIEWS as v (v.token)}
			{@const on = hasToken(queryText, v.token)}
			<button
				type="button"
				class="rounded-full border px-2.5 py-0.5 text-xs transition-colors {on
					? 'border-foreground/40 bg-foreground text-background'
					: 'border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground'}"
				aria-pressed={on}
				onclick={() => toggleToken(v.token)}
			>
				{v.label}
			</button>
		{/each}
		{#if scansStore.filters.startedFrom}
			<span
				class="ml-1 inline-flex items-center gap-1 rounded-full border border-border bg-background px-2 py-0.5 text-xs"
			>
				Started {formatShortDate(scansStore.filters.startedFrom)}{scansStore.filters.startedTo
					? ` to ${formatShortDate(new Date(new Date(scansStore.filters.startedTo).getTime() - 1))}`
					: ' onward'}
				<button
					type="button"
					aria-label="Remove date filter"
					class="text-muted-foreground hover:text-foreground"
					onclick={() => scansStore.setRange(null, null)}
				>
					<X class="size-3" />
				</button>
			</span>
		{/if}
		{#if scansStore.hasActiveFilters}
			<button
				type="button"
				class="ml-auto text-xs text-muted-foreground hover:text-foreground"
				onclick={() => {
					queryText = '';
					scansStore.clearFilters();
				}}
			>
				Clear all
			</button>
		{/if}
	</div>

	{#if scansStore.isLoading && scans.length === 0}
		<TableSkeleton
			lead={[{ key: 'name', label: 'Target', width: 'min-w-0 flex-1' }]}
			actions={false}
			selectable
		/>
	{:else if scansStore.error && scans.length === 0}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Media class="size-12 rounded-2xl bg-destructive/10">
					<TriangleAlert class="size-6 text-destructive" />
				</Empty.Media>
				<Empty.Title>Scans not loaded</Empty.Title>
				<Empty.Description class="max-w-md">{scansStore.error}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button variant="outline" class="gap-2" onclick={() => scansStore.refresh()}>
					<RefreshCw class="size-4" /> Retry
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if scans.length === 0 && scansStore.hasActiveFilters}
		<Empty.Root class="py-16">
			<Empty.Header><Empty.Title>No runs match</Empty.Title></Empty.Header>
			<Empty.Content>
				<Button
					size="sm"
					variant="outline"
					class="gap-2"
					onclick={() => {
						queryText = '';
						scansStore.clearFilters();
					}}
				>
					<X class="size-4" /> Clear filters
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if scans.length === 0}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Media variant="icon" class="size-14 rounded-2xl bg-muted text-muted-foreground/60">
					<History />
				</Empty.Media>
				<Empty.Title>No scans</Empty.Title>
			</Empty.Header>
			{#if onLaunch}
				<Empty.Content>
					<Button class="gap-2" onclick={onLaunch}><Plus class="size-4" /> New scan</Button>
				</Empty.Content>
			{/if}
		</Empty.Root>
	{:else}
		<ScrollArea orientation="horizontal">
			<div class="w-full min-w-[720px]" role="table" aria-label="Scan runs">
				<div
					class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
					role="row"
				>
					<div class="{COL.select} flex items-center">
						<Checkbox
							checked={selectAll === true}
							indeterminate={selectAll === 'indeterminate'}
							onCheckedChange={toggleSelectAll}
							aria-label="Select all runs"
						/>
					</div>
					<div class={COL.target}>{targetId ? 'Engine' : 'Target'}</div>
					<div class={COL.status}>Status</div>
					{@render sortHead('Findings', 'vulnerabilities', `${COL.findings} flex`)}
					{#if historyPrefs.shows('assets')}<div class={COL.assets}>Assets</div>{/if}
					{#if historyPrefs.shows('change')}<div class={COL.change}>Change</div>{/if}
					{#if historyPrefs.shows('engine')}<div class={COL.engine}>Engine</div>{/if}
					{#if historyPrefs.shows('duration')}{@render sortHead(
							'Duration',
							'duration',
							COL.duration
						)}{/if}
					{@render sortHead('Started', 'started', COL.started)}
					<div class={COL.actions}></div>
				</div>
				{#each visible as v (v.scan.id)}
					<ScanRow
						{projectId}
						scan={v.scan}
						showTarget={!targetId}
						trend={v.nested ? undefined : scansStore.trends[v.scan.target_id]}
						{now}
						nested={v.nested}
						expanded={expanded.has(v.scan.id)}
						focused={focusId === v.scan.id}
						selected={selected.has(v.scan.id)}
						flash={flashId === v.scan.id}
						earlierOpen={!!earlier[v.scan.id]}
						onEarlier={latest && !v.nested ? () => toggleEarlier(v.scan) : undefined}
						onToggle={() => toggleExpand(v.scan.id)}
						onSelect={() =>
							selected.has(v.scan.id) ? selected.delete(v.scan.id) : selected.add(v.scan.id)}
						onFocus={() => (focusId = v.scan.id)}
						onOpen={() => goto(ROUTES.scan(v.scan.id))}
						onCompare={() => openCompare(v.scan)}
						onRescan={() => onRescan?.(v.scan)}
						onPause={() => pause(v.scan)}
						onResume={() => resume(v.scan)}
						onCancel={() => (cancelTarget = v.scan)}
						onDelete={() => (deleteTarget = v.scan)}
						onJump={jump}
						onChanged={changed}
					/>
					{#if !v.nested && earlier[v.scan.id] === 'loading'}
						<div class="flex items-center gap-3 border-b py-2.5 pr-4 pl-10" aria-busy="true">
							<Skeleton class="h-4 w-48" />
							<Skeleton class="ml-auto h-4 w-24" />
							<Skeleton class="h-4 w-16" />
						</div>
					{/if}
				{/each}
			</div>
		</ScrollArea>
		<div class="flex flex-wrap items-center justify-between gap-3 border-t bg-muted/20 px-4 py-3">
			<div class="flex items-center gap-4">
				<span class="text-xs text-muted-foreground">
					{scans.length} of {pagination.totalItems}
					{latest
						? pagination.totalItems === 1
							? 'target'
							: 'targets'
						: pagination.totalItems === 1
							? 'run'
							: 'runs'}
				</span>
				<PageSizeSelector
					pageSize={pagination.pageSize}
					onPageSizeChange={(size) => scansStore.setPageSize(size)}
				/>
			</div>
			{#if pagination.pageSize !== -1 && pagination.totalPages > 1}
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
									<Pagination.Item
										><Pagination.Link page={p} isActive={currentPage === p.value}
											>{p.value}</Pagination.Link
										></Pagination.Item
									>
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

<CompareSheet
	{projectId}
	current={compare?.current ?? null}
	baseline={compare?.baseline ?? null}
	onClose={() => (compare = null)}
/>

<Dialog.Root bind:open={shortcutsOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header><Dialog.Title>Keyboard shortcuts</Dialog.Title></Dialog.Header>
		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
			{#each SHORTCUTS as [k, label] (k)}
				<dt><Kbd>{k}</Kbd></dt>
				<dd class="text-muted-foreground">{label}</dd>
			{/each}
		</dl>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={!!cancelTarget}
	title="Cancel scan"
	description="The scan stops and is marked cancelled."
	confirmLabel="Cancel scan"
	cancelLabel="Keep running"
	onOpenChange={(o) => !o && (cancelTarget = null)}
	onConfirm={confirmCancel}
/>

<ConfirmDialog
	open={!!deleteTarget}
	title="Delete scan"
	description="Scan {deleteTarget?.execution_config.target_value ??
		''} and its results are removed."
	confirmLabel="Delete"
	cancelLabel="Keep"
	destructive
	onOpenChange={(o) => !o && (deleteTarget = null)}
	onConfirm={confirmDelete}
/>

<ScanBulkActionBar
	selectedCount={selectedScans.length}
	liveCount={selectedLive}
	targetCount={selectedTargets.length}
	{compareHref}
	compareReason={pair.reason}
	onRescan={() => {
		onRescanMany?.(selectedTargets);
		selected.clear();
	}}
	onCancel={() => (bulkCancelOpen = true)}
	onDelete={() => (bulkDeleteOpen = true)}
	onClear={() => selected.clear()}
/>

<ConfirmDialog
	open={bulkDeleteOpen}
	title="Delete {selectedScans.length} scan{selectedScans.length !== 1 ? 's' : ''}"
	description="The selected scans and their results are removed."
	confirmLabel="Delete {selectedScans.length}"
	cancelLabel="Keep"
	destructive
	onOpenChange={(o) => (bulkDeleteOpen = o)}
	onConfirm={confirmBulkDelete}
/>

<ConfirmDialog
	open={cancelAllOpen}
	title="Cancel all unfinished scans"
	description="Running, queued and paused scans stop and are marked cancelled."
	confirmLabel="Cancel scans"
	cancelLabel="Keep"
	onOpenChange={(o) => (cancelAllOpen = o)}
	onConfirm={confirmCancelAll}
/>

<ConfirmDialog
	open={bulkCancelOpen}
	title="Cancel {selectedLive} unfinished scan{selectedLive !== 1 ? 's' : ''}"
	description="The selected scans stop and are marked cancelled."
	confirmLabel="Cancel scans"
	cancelLabel="Keep"
	onOpenChange={(o) => (bulkCancelOpen = o)}
	onConfirm={confirmBulkCancel}
/>
