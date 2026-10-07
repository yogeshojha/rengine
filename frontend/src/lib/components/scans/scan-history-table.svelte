<script lang="ts">
	import SevCountChip from '$lib/components/sev-count-chip.svelte';
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
	import * as Empty from '$lib/components/ui/empty';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Badge } from '$lib/components/ui/badge';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { HISTORY_DAYS, scansStore } from '$lib/stores/scans.svelte';
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
	import { plural, pluralWord } from '$lib/utilities/strings';
	import type { ScanRead, ScanSortKey } from '$lib/types/scan';

	import ScanStatusTabs from './scan-status-tabs.svelte';
	import ScanBulkActionBar from './scan-bulk-action-bar.svelte';
	import ScanRow from './history/scan-row.svelte';
	import HistoryChart from './history/history-chart.svelte';
	import CompareSheet from './history/compare-sheet.svelte';
	import { COL } from './history/columns';
	import { forgetFindings } from './history/findings';
	import {
		BRIEF_TABS,
		HISTORY_COLUMNS,
		HISTORY_COLUMN_LABELS,
		STRIP_SEVERITIES,
		historyPrefs,
		runBriefTabs
	} from './history/prefs.svelte';

	interface Props {
		targetId?: string;
		targetIds?: string[];
		onLaunch?: () => void;
		onRescan?: (scan: ScanRead) => void;
		onRescanMany?: (targetIds: string[]) => void;
		scopeLabel?: string;
		onClearScope?: () => void;
	}

	let { targetId, targetIds, onLaunch, onRescan, onRescanMany, scopeLabel, onClearScope }: Props =
		$props();

	const PAGE_SIZES = [10, 20, 25, 50, 100];

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
	let cancelling = $state(false);
	let deleting = $state(false);
	let bulkDeleting = $state(false);
	let bulkCancelling = $state(false);
	let cancellingAll = $state(false);
	let shortcutsOpen = $state(false);
	let now = $state(Date.now());
	let searchEl = $state<HTMLInputElement | null>(null);
	let queryText = $derived(scansStore.filters.query);
	let compare = $state<{ current: string; baseline: string | null } | null>(null);

	let expanded = new SvelteSet<string>();
	let earlier = $state<Record<string, ScanRead[] | 'loading'>>({});
	let focusId = $state<string | null>(null);
	const selected = new SvelteSet<string>();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let scoped = $derived(!!onClearScope && (targetIds?.length ?? 0) > 0);
	let filtered = $derived(scansStore.hasActiveFilters || scoped);

	function clearAll() {
		scansStore.clearFilters();
		if (scoped) onClearScope?.();
	}

	$effect(() => {
		const project = projectsStore.activeProject;
		const ids = targetId ? [targetId] : (targetIds ?? []);
		if (project && projectsStore.hasFetched) {
			untrack(() => scansStore.init(project.id, ids));
		}
	});

	$effect(() => {
		const t = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(t);
	});

	$effect(() => {
		if (!scansStore.hasLive) return;
		untrack(() => engineCatalogStore.fetch());
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
	let windowTotals = $derived(scansStore.daily?.window ?? null);
	let windowRuns = $derived(windowTotals?.runs ?? 0);
	let byStatus = $derived(scansStore.stats?.by_status);
	let openCount = $derived(byStatus ? byStatus.running + byStatus.pending + byStatus.paused : 0);
	let canCancelAll = $derived(openCount > 0 || scansStore.hasLive);
	let sevRuns = $derived(
		STRIP_SEVERITIES.map((s) => ({
			sev: s,
			n: windowTotals?.[s as 'critical' | 'high' | 'medium'] ?? 0,
			active: hasToken(scansStore.filters.query, `severity:${s}`)
		}))
	);

	let visible = $derived.by(() => {
		const out: { scan: ScanRead; nested: boolean }[] = [];
		// eslint-disable-next-line svelte/prefer-svelte-reactivity
		const seen = new Set(scans.map((s) => s.id));
		for (const s of scans) {
			out.push({ scan: s, nested: false });
			const kids = latest ? earlier[s.id] : undefined;
			if (!Array.isArray(kids)) continue;
			for (const k of kids) {
				if (seen.has(k.id)) continue;
				seen.add(k.id);
				out.push({ scan: k, nested: true });
			}
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
		scansStore.setQuery(q, immediate);
	}

	function toggleToken(token: string) {
		setQuery(
			hasToken(queryText, token) ? withoutToken(queryText, token) : withToken(queryText, token),
			true
		);
	}

	let activeViews = $derived(
		SAVED_VIEWS.filter((v) => hasToken(queryText, v.token)).map((v) => v.token)
	);
	let engineCount = $derived(
		(scansStore.stats?.engines ?? []).filter((e) => hasToken(queryText, `engine:${quote(e.name)}`))
			.length
	);
	let dateLabel = $derived(
		scansStore.filters.startedFrom
			? `Started ${formatShortDate(scansStore.filters.startedFrom, true)}${
					scansStore.filters.startedTo
						? ` to ${formatShortDate(new Date(new Date(scansStore.filters.startedTo).getTime() - 1), true)}`
						: ' onward'
				}`
			: ''
	);

	function setViews(next: string[]) {
		const changed = SAVED_VIEWS.find(
			(v) => next.includes(v.token) !== activeViews.includes(v.token)
		);
		if (changed) toggleToken(changed.token);
	}

	function toggleSeverity(sev: string) {
		const token = `severity:${sev}`;
		if (!hasToken(queryText, token)) {
			scansStore.filters.latest = false;
			if (scansStore.daily && !scansStore.filters.startedFrom)
				scansStore.filters.startedFrom = scansStore.daily.since;
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
		await tick();
		document
			.getElementById(`scan-row-${scanId}`)
			?.scrollIntoView({ block: 'center', behavior: 'smooth' });
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
		if (!s || cancelling) return;
		cancelling = true;
		const ok = await scansStore.cancel(s);
		cancelling = false;
		if (ok) {
			cancelTarget = null;
			toast.success('Scan cancelled');
		} else toast.error(scansStore.error ?? 'Scan not cancelled');
	}

	async function confirmDelete() {
		const s = deleteTarget;
		if (!s || deleting) return;
		deleting = true;
		const ok = await scansStore.remove(s);
		deleting = false;
		if (ok) {
			deleteTarget = null;
			toast.success('Scan deleted');
		} else toast.error(scansStore.error ?? 'Scan not deleted');
	}

	async function confirmBulkDelete() {
		const ids = [...selected];
		if (!ids.length) {
			bulkDeleteOpen = false;
			return;
		}
		bulkDeleting = true;
		const { ok, failed } = await scansStore.removeMany(ids);
		bulkDeleting = false;
		if (ok) {
			bulkDeleteOpen = false;
			selected.clear();
			toast.success(`${plural(ok, 'scan')} deleted`);
		}
		if (failed) toast.error(`${plural(failed, 'scan')} not deleted`);
	}

	async function confirmBulkCancel() {
		const ids = selectedScans.filter((s) => isOpenStatus(s.status)).map((s) => s.id);
		if (!ids.length) {
			bulkCancelOpen = false;
			return;
		}
		bulkCancelling = true;
		const { ok, failed } = await scansStore.cancelMany(ids);
		bulkCancelling = false;
		if (ok) {
			bulkCancelOpen = false;
			toast.success(`${plural(ok, 'scan')} cancelled`);
		}
		if (failed) toast.error(`${plural(failed, 'scan')} not cancelled`);
	}

	async function confirmCancelAll() {
		cancellingAll = true;
		const n = await scansStore.cancelAll();
		cancellingAll = false;
		if (n === null) toast.error(scansStore.error ?? 'Scans not cancelled');
		else {
			cancelAllOpen = false;
			toast.success(`${plural(n, 'scan')} cancelled`);
		}
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

	const OWN_KEYS = new Set(['Enter', ' ', 'ArrowUp', 'ArrowDown']);
	const interactive = (e: KeyboardEvent) =>
		!!(e.target as HTMLElement | null)?.closest?.(
			'button, a, [role=button], [role=checkbox], [role=tab], [role=option], [role=radio], [role=switch]'
		);

	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === '/' && !typing(e)) {
			e.preventDefault();
			searchEl?.focus();
			return;
		}
		if (typing(e) || document.querySelector('[role=dialog],[role=menu]')) return;
		if (OWN_KEYS.has(e.key) && interactive(e)) return;
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
					runBriefTabs.set(focused.id, BRIEF_TABS[Number(e.key) - 1]);
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

{#snippet sortHead(label: string, key: ScanSortKey, cls: string, end = false)}
	{@const active = scansStore.filters.sortKey === key}
	<div
		class={cls}
		role="columnheader"
		aria-sort={active
			? scansStore.filters.sortDir === 'desc'
				? 'descending'
				: 'ascending'
			: undefined}
	>
		<button
			type="button"
			class="flex w-full items-center gap-1 text-left tracking-wide uppercase hover:text-foreground {end
				? 'justify-end'
				: ''} {active ? 'text-foreground' : ''}"
			onclick={() => sortBy(key)}
		>
			{label}
			{#if active}
				{#if scansStore.filters.sortDir === 'desc'}<ArrowDown class="size-3" />{:else}<ArrowUp
						class="size-3"
					/>{/if}
			{/if}
		</button>
	</div>
{/snippet}

{#snippet chip(label: string, removeLabel: string, onRemove: () => void, labelClass = '')}
	<Badge
		variant="outline"
		class="ml-1 max-w-full min-w-0 gap-1 overflow-visible bg-background pr-0.5 font-normal"
	>
		<span class="min-w-0 truncate {labelClass}" title={label}>{label}</span>
		<Button
			variant="ghost"
			size="icon-xs"
			class="size-4 shrink-0 rounded-full text-muted-foreground hover:text-foreground"
			aria-label={removeLabel}
			onclick={onRemove}
		>
			<X class="size-3" />
		</Button>
	</Badge>
{/snippet}

<Card.Root class="gap-0 overflow-hidden py-0">
	<!-- strip -->
	<div class="grid gap-x-8 gap-y-4 border-b px-4 py-4 lg:grid-cols-[auto_minmax(0,1fr)]">
		<div class="flex flex-wrap items-start gap-x-8 gap-y-3">
			<div class="flex flex-col gap-0.5">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase"
					>Runs · {HISTORY_DAYS} days</span
				>
				<span class="font-mono text-2xl font-semibold tabular-nums"
					>{windowRuns.toLocaleString()}</span
				>
			</div>
			<div class="flex flex-col gap-0.5">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase">Running now</span>
				<span class="flex items-center gap-2 font-mono text-2xl font-semibold tabular-nums">
					{byStatus?.running ?? 0}
					{#if (byStatus?.running ?? 0) > 0}
						<span class="size-2 rounded-full bg-info" aria-hidden="true"></span>
					{/if}
				</span>
				<span class="text-2xs text-muted-foreground">
					{byStatus?.pending ?? 0} queued · {byStatus?.paused ?? 0} paused
				</span>
			</div>
			<div class="flex flex-col gap-1">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase"
					>Runs with findings · {HISTORY_DAYS} days</span
				>
				<div class="flex items-center gap-1.5">
					{#each sevRuns as s (s.sev)}
						<SevCountChip
							severity={s.sev}
							count={s.n}
							pressed={s.active}
							aria-label="Runs with {SEVERITY_LABELS[s.sev].toLowerCase()} findings: {s.n}"
							onclick={() => toggleSeverity(s.sev)}
						/>
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
			<InputGroup.Root>
				<InputGroup.Addon><Search /></InputGroup.Addon>
				<InputGroup.Input
					bind:ref={searchEl}
					id="scan-history-search"
					class="font-mono placeholder:font-sans"
					placeholder={targetId
						? 'engine:default severity:critical status:failed is:added'
						: 'target:acme severity:critical status:failed is:added'}
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
				<InputGroup.Addon align="inline-end">
					{#if queryText}
						<InputGroup.Button
							size="icon-xs"
							aria-label="Clear search"
							onclick={() => setQuery('', true)}><X /></InputGroup.Button
						>
					{:else}
						<Kbd class="hidden sm:inline-flex">/</Kbd>
					{/if}
				</InputGroup.Addon>
			</InputGroup.Root>
			{#if parseError}
				<p id="scan-history-search-error" class="text-2xs text-destructive">{parseError}</p>
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-2">
			{#if scansStore.stats?.engines?.length}
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="outline"
								class={engineCount ? 'border-primary/50 bg-primary/5' : ''}
								aria-label={engineCount ? `Engine, ${engineCount} selected` : 'Engine'}
							>
								Engine
								{#if engineCount}
									<Badge variant="secondary" class="h-5 px-1.5 text-xs">{engineCount}</Badge>
								{/if}
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-56">
						{#each scansStore.stats.engines as e (e.name)}
							{@const token = `engine:${quote(e.name)}`}
							<DropdownMenu.CheckboxItem
								checked={hasToken(queryText, token)}
								onCheckedChange={() => toggleToken(token)}
								closeOnSelect={false}
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
						<Button {...props} variant="outline" size="icon" aria-label="Columns and density">
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
						class="hidden sm:inline-flex"
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
				<Button onclick={onLaunch}><Plus class="size-4" /> New scan</Button>
			{/if}
		</div>
	</div>

	<!-- saved views and active filters -->
	<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
		<ToggleGroup.Root
			type="multiple"
			variant="outline"
			size="sm"
			spacing={1}
			value={activeViews}
			onValueChange={setViews}
			aria-label="Saved views"
			class="flex-wrap"
		>
			{#each SAVED_VIEWS as v (v.token)}
				<ToggleGroup.Item
					value={v.token}
					class="rounded-full font-normal data-[state=on]:border-primary/50 data-[state=on]:bg-primary/5"
				>
					{v.label}
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
		{#if scoped}
			{@render chip(
				scopeLabel ?? '',
				'Remove target filter',
				() => onClearScope?.(),
				targetIds?.length === 1 ? 'font-mono' : 'tabular-nums'
			)}
		{/if}
		{#if scansStore.filters.startedFrom}
			{@render chip(dateLabel, 'Remove date filter', () => scansStore.setRange(null, null))}
		{/if}
		{#if filtered}
			<Button variant="ghost" size="xs" class="ml-auto text-muted-foreground" onclick={clearAll}>
				Clear all
			</Button>
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
				<Button size="sm" variant="outline" onclick={() => scansStore.refresh()}>
					<RefreshCw class="size-4" /> Retry
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if scans.length === 0 && filtered}
		<Empty.Root class="py-16">
			<Empty.Header><Empty.Title>No runs match</Empty.Title></Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" onclick={clearAll}>
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
					<Button size="sm" onclick={onLaunch}><Plus class="size-4" /> New scan</Button>
				</Empty.Content>
			{/if}
		</Empty.Root>
	{:else}
		<div class="@container/scans overflow-x-auto">
			<div class="w-full min-w-[720px]" role="table" aria-label="Scans">
				<div
					class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
					role="row"
				>
					<div class="{COL.select} flex items-center" role="columnheader">
						<Checkbox
							checked={selectAll === true}
							indeterminate={selectAll === 'indeterminate'}
							onCheckedChange={toggleSelectAll}
							aria-label="Select all runs"
						/>
					</div>
					<div class={COL.target} role="columnheader">{targetId ? 'Engine' : 'Target'}</div>
					<div class={COL.status} role="columnheader">Status</div>
					{@render sortHead('Findings', 'vulnerabilities', `${COL.findings} flex`)}
					{#if historyPrefs.shows('assets')}
						<div class={COL.assets} role="columnheader">Assets</div>
					{/if}
					{#if historyPrefs.shows('change')}
						<div class={COL.change} role="columnheader">Change</div>
					{/if}
					{#if !targetId && historyPrefs.shows('engine')}
						<div class={COL.engine} role="columnheader">Engine</div>
					{/if}
					{#if historyPrefs.shows('duration')}
						{@render sortHead('Duration', 'duration', COL.duration, true)}
					{/if}
					{@render sortHead('Started', 'started', COL.started, true)}
					<div class={COL.actions} role="columnheader"><span class="sr-only">Actions</span></div>
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
						earlierOpen={!!earlier[v.scan.id]}
						onEarlier={latest && !v.nested ? () => toggleEarlier(v.scan) : undefined}
						onToggle={() => toggleExpand(v.scan.id)}
						onSelect={() =>
							selected.has(v.scan.id) ? selected.delete(v.scan.id) : selected.add(v.scan.id)}
						onOpen={() => goto(ROUTES.scan(v.scan.id))}
						onCompare={() => openCompare(v.scan)}
						onRescan={onRescan ? () => onRescan?.(v.scan) : undefined}
						onPause={() => pause(v.scan)}
						onResume={() => resume(v.scan)}
						onCancel={() => (cancelTarget = v.scan)}
						onDelete={() => (deleteTarget = v.scan)}
						onJump={jump}
						onChanged={changed}
					/>
					{#if !v.nested && earlier[v.scan.id] === 'loading'}
						<div role="row">
							<div
								class="flex items-center gap-3 border-b py-2.5 pr-4 pl-10"
								role="cell"
								aria-busy="true"
							>
								<Skeleton class="h-4 w-48" />
								<Skeleton class="ml-auto h-4 w-24" />
								<Skeleton class="h-4 w-16" />
							</div>
						</div>
					{/if}
				{/each}
			</div>
		</div>
		<ResultsPagination
			total={pagination.totalItems}
			page={pagination.currentPage - 1}
			pageSize={pagination.pageSize}
			noun={latest ? 'target' : 'run'}
			sizes={PAGE_SIZES}
			onPage={(p) => scansStore.setPage(p + 1)}
			onPageSize={(size) => scansStore.setPageSize(size)}
		/>
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
	destructive
	loading={cancelling}
	loadingLabel="Cancelling"
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
	loading={deleting}
	loadingLabel="Deleting"
	onOpenChange={(o) => !o && (deleteTarget = null)}
	onConfirm={confirmDelete}
/>

<ScanBulkActionBar
	selectedCount={selectedScans.length}
	liveCount={selectedLive}
	targetCount={onRescanMany ? selectedTargets.length : 0}
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
	title="Delete {plural(selectedScans.length, 'scan')}"
	description="The selected scans and their results are removed."
	confirmLabel="Delete {selectedScans.length}"
	cancelLabel="Keep"
	destructive
	loading={bulkDeleting}
	loadingLabel="Deleting"
	onOpenChange={(o) => (bulkDeleteOpen = o)}
	onConfirm={confirmBulkDelete}
/>

<ConfirmDialog
	open={cancelAllOpen}
	title="Cancel all unfinished scans"
	description="Running, queued and paused scans stop and are marked cancelled."
	confirmLabel="Cancel scans"
	cancelLabel="Keep"
	destructive
	loading={cancellingAll}
	loadingLabel="Cancelling"
	onOpenChange={(o) => (cancelAllOpen = o)}
	onConfirm={confirmCancelAll}
/>

<ConfirmDialog
	open={bulkCancelOpen}
	title="Cancel {selectedLive} unfinished {pluralWord(selectedLive, 'scan')}"
	description="The selected scans stop and are marked cancelled."
	confirmLabel="Cancel scans"
	cancelLabel="Keep"
	destructive
	loading={bulkCancelling}
	loadingLabel="Cancelling"
	onOpenChange={(o) => (bulkCancelOpen = o)}
	onConfirm={confirmBulkCancel}
/>
