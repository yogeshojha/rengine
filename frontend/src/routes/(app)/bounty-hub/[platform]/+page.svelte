<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack, tick } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import FileText from '@lucide/svelte/icons/file-text';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Search from '@lucide/svelte/icons/search';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';
	import Keyboard from '@lucide/svelte/icons/keyboard';
	import Rows3 from '@lucide/svelte/icons/rows-3';

	import * as Card from '$lib/components/ui/card';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import MonthChart from '$lib/components/bounty-hub/reports/month-chart.svelte';
	import ReportRow from '$lib/components/bounty-hub/reports/report-row.svelte';
	import ProgramsTable from '$lib/components/bounty-hub/reports/programs-table.svelte';
	import { RCOL } from '$lib/components/bounty-hub/reports/columns';

	import { bountyReportsApi } from '$lib/api/bounty-reports';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { REFRESH_POLLS, REFRESH_POLL_MS } from '$lib/config/bounty-programs';
	import {
		REPORT_PAGE_SIZE,
		REPORT_PAGE_SIZES,
		REPORT_SAVED_VIEWS,
		REPORT_SEVERITY_KEY,
		REPORT_STAGE_ORDER,
		formatMonies
	} from '$lib/config/bounty-reports';
	import { SEVERITY_CHIP, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { externalHref, openExternal } from '$lib/utilities/links';
	import {
		ALL_TAB,
		PAID_TAB,
		ReportSort,
		ReportView,
		type BountyAccountSummary,
		type BountyReport,
		type BountyReportFilters,
		type ProgramReports,
		type ReportCounts
	} from '$lib/types/bounty-report';

	let platform = $derived(page.params.platform ?? '');
	let spec = $derived(bountyVocabulary.platform(platform));
	let label = $derived(spec?.label ?? platform);
	let platformUrl = $derived(spec?.url ?? '');

	let connected = $state<boolean | null>(null);
	let summary = $state<BountyAccountSummary | null>(null);
	let programs = $state<ProgramReports[]>([]);
	let reports = $state<BountyReport[]>([]);
	let total = $state(0);
	let counts = $state<ReportCounts | null>(null);
	let loading = $state(true);
	let failed = $state<string | null>(null);
	let accountFailed = $state<string | null>(null);
	let programQuery = $state('');
	let shortcutsOpen = $state(false);
	let listSeq = 0;
	let countSeq = 0;
	let refreshingFor = $state<string | null>(null);
	const refreshing = $derived(refreshingFor === platform);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	let compact = $state(false);
	let searchEl = $state<HTMLInputElement | null>(null);
	let focusId = $state<string | null>(null);
	const expanded = new SvelteSet<string>();

	// ---------- url state ----------
	let sp = $derived(page.url.searchParams);
	let queryText = $derived(sp.get('q') ?? '');
	let view = $derived((sp.get('view') as ReportView) ?? ReportView.Reports);
	let filters = $derived<BountyReportFilters>({
		tab: sp.get('tab') ?? ALL_TAB,
		states: sp.getAll('state'),
		programs: sp.getAll('program'),
		severities: sp.getAll('severity'),
		q: sp.get('q') ?? '',
		from: sp.get('from'),
		to: sp.get('to'),
		sort: (sp.get('sort') as ReportSort) ?? ReportSort.Submitted,
		order: sp.get('order') === 'asc' ? 'asc' : 'desc'
	});
	let pageIndex = $derived(Math.max(1, Math.floor(Number(sp.get('page'))) || 1));
	let pageSize = $derived(Number(sp.get('size') ?? REPORT_PAGE_SIZE) || REPORT_PAGE_SIZE);
	let listKey = $derived(JSON.stringify([platform, filters, pageIndex, pageSize]));
	let countKey = $derived(JSON.stringify([platform, { ...filters, tab: '', sort: '', order: '' }]));
	let hasFilters = $derived(
		filters.states.length > 0 ||
			filters.programs.length > 0 ||
			filters.severities.length > 0 ||
			!!filters.q ||
			!!filters.from
	);

	function update(mut: (s: URLSearchParams) => void, keepPage = false) {
		const url = new URL(page.url);
		mut(url.searchParams);
		if (!keepPage) url.searchParams.delete('page');
		void goto(url, { replaceState: true, noScroll: true, keepFocus: true });
	}

	const setList = (key: string, values: string[]) =>
		update((s) => {
			s.delete(key);
			for (const v of values) s.append(key, v);
		});

	const toggleIn = (key: string, value: string, list: string[]) =>
		setList(key, list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

	function setParam(key: string, value: string | null, keepPage = false) {
		update((s) => (value ? s.set(key, value) : s.delete(key)), keepPage);
	}

	function onlyProgram(handle: string) {
		update((s) => {
			for (const k of ['program', 'view', 'q', 'tab']) s.delete(k);
			s.append('program', handle);
		});
	}

	function search(text: string) {
		queryText = text;
		setParam('q', text.trim() || null);
	}

	function clearFilters() {
		queryText = '';
		update((s) => {
			for (const k of ['state', 'program', 'severity', 'q', 'from', 'to', 'tab']) s.delete(k);
		});
	}

	function sortBy(key: ReportSort) {
		update((s) => {
			if (filters.sort === key) s.set('order', filters.order === 'desc' ? 'asc' : 'desc');
			else {
				s.set('sort', key);
				s.set('order', key === ReportSort.Program ? 'asc' : 'desc');
			}
		});
	}

	function applyView(v: (typeof REPORT_SAVED_VIEWS)[number]) {
		const on = savedOn(v);
		update((s) => {
			s.delete('state');
			s.delete('severity');
			if (on) return;
			for (const st of v.states ?? []) s.append('state', st);
			for (const sv of v.severities ?? []) s.append('severity', sv);
		});
	}

	const same = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));
	const savedOn = (v: (typeof REPORT_SAVED_VIEWS)[number]) =>
		same(filters.states, v.states ?? []) && same(filters.severities, v.severities ?? []);

	// ---------- loading ----------
	async function loadAccount(p: string) {
		accountFailed = null;
		try {
			const status = await bountyProgramsApi.status();
			connected = status.platforms.some((x) => x.platform === p && x.configured);
			if (!connected) {
				loading = false;
				return;
			}
			const [s, progs] = await Promise.all([
				bountyReportsApi.summary(p),
				bountyReportsApi.programs(p)
			]);
			summary = s;
			programs = progs;
		} catch (error) {
			accountFailed = error instanceof Error ? error.message : 'Reports not loaded';
			loading = false;
		}
	}

	async function loadList(p: string, f: BountyReportFilters, index: number, size: number) {
		const seq = ++listSeq;
		loading = true;
		try {
			const res = await bountyReportsApi.list(p, f, index, size);
			if (seq !== listSeq) return;
			const last = Math.max(1, Math.ceil(res.total / size));
			if (res.total > 0 && index > last) {
				setParam('page', String(last), true);
				return;
			}
			reports = res.items;
			total = res.total;
			failed = null;
		} catch (error) {
			if (seq !== listSeq) return;
			failed = error instanceof Error ? error.message : 'Reports not loaded';
			reports = [];
			total = 0;
		} finally {
			if (seq === listSeq) loading = false;
		}
	}

	function loadCounts(p: string, f: BountyReportFilters) {
		const seq = ++countSeq;
		bountyReportsApi
			.counts(p, f)
			.then((c) => seq === countSeq && (counts = c))
			.catch(() => seq === countSeq && (counts = null));
	}

	$effect(() => {
		const p = platform;
		untrack(() => {
			void bountyVocabulary.load();
			void loadAccount(p);
		});
	});

	$effect(() => {
		if (label) breadcrumbStore.set(platform, label);
	});

	$effect(() => {
		void listKey;
		if (connected !== true) return;
		untrack(() => loadList(platform, filters, pageIndex, pageSize));
	});

	$effect(() => {
		void countKey;
		if (connected !== true) return;
		untrack(() => loadCounts(platform, filters));
	});

	async function refresh() {
		const p = platform;
		refreshingFor = p;
		const before = summary?.synced_at ?? null;
		const beforeError = summary?.error ?? null;
		try {
			await bountyReportsApi.sync(p);
			let done = false;
			for (let i = 0; i < REFRESH_POLLS && !done; i++) {
				await new Promise((r) => setTimeout(r, REFRESH_POLL_MS));
				if (platform !== p) return;
				const next = await bountyReportsApi.summary(p).catch(() => null);
				if (platform !== p) return;
				if (next && (next.synced_at !== before || (next.error && next.error !== beforeError))) {
					summary = next;
					done = true;
				}
			}
			const progs = await bountyReportsApi.programs(p);
			if (platform !== p) return;
			programs = progs;
			await loadList(p, filters, pageIndex, pageSize);
			loadCounts(p, filters);
			if (summary?.error) toast.error(summary.error);
			else toast.success(done ? 'Reports refreshed' : 'Refresh running');
		} catch (error) {
			if (platform !== p) return;
			toast.error(error instanceof Error ? error.message : 'Refresh not started');
		} finally {
			if (refreshingFor === p) refreshingFor = null;
		}
	}

	// ---------- derived ----------
	let programMap = $derived(new Map(programs.map((p) => [p.handle, p])));
	let programName = (h: string) => programMap.get(h)?.name ?? h;
	let stateLabel = (s: string) =>
		bountyVocabulary.vocabulary?.report_states.find((x) => x.key === s)?.label ?? s;
	let severityLabel = (s: string) => SEVERITY_LABELS[REPORT_SEVERITY_KEY[s] ?? s] ?? s;
	let payments = $derived((summary?.earned ?? []).reduce((n, m) => n + m.awards, 0));
	let resolvedShare = $derived(
		summary?.reports ? Math.round(((summary.stages.resolved ?? 0) / summary.reports) * 100) : 0
	);

	let tabs = $derived([
		{ key: ALL_TAB, label: 'All' },
		...REPORT_STAGE_ORDER.map((s) => ({ key: s, label: bountyVocabulary.stageLabel(s) })),
		{ key: PAID_TAB, label: 'Paid' }
	]);

	// ---------- keyboard ----------
	function typing(e: KeyboardEvent): boolean {
		const el = e.target as HTMLElement | null;
		return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
	}

	async function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === '/' && !typing(e)) {
			e.preventDefault();
			searchEl?.focus();
			return;
		}
		if (typing(e) || view !== ReportView.Reports) return;
		if ((e.target as HTMLElement | null)?.closest('button,a,[role=button],[role=option]')) return;
		if (document.querySelector('[role=dialog],[role=menu]')) return;
		const idx = reports.findIndex((r) => r.id === focusId);
		const focused = idx >= 0 ? reports[idx] : null;
		const move = async (d: number) => {
			const next = reports[Math.max(0, Math.min(reports.length - 1, (idx < 0 ? -1 : idx) + d))];
			if (!next) return;
			focusId = next.id;
			await tick();
			document.getElementById(`report-row-${next.id}`)?.scrollIntoView({ block: 'nearest' });
		};
		switch (e.key) {
			case 'j':
			case 'ArrowDown':
				e.preventDefault();
				await move(1);
				break;
			case 'k':
			case 'ArrowUp':
				e.preventDefault();
				await move(-1);
				break;
			case 'o':
				if (focused) toggle(focused.id);
				break;
			case 'Enter':
				if (focused) openExternal(focused.url);
				break;
			case 'p':
				if (focused?.program_handle) onlyProgram(focused.program_handle);
				break;
			case '?':
				shortcutsOpen = true;
				break;
			case 'Escape':
				if (focused && expanded.has(focused.id)) expanded.delete(focused.id);
				break;
		}
	}

	const SHORTCUTS: [string, string][] = [
		['j / k', 'Move between reports'],
		['o', 'Expand or collapse the report'],
		['p', 'Filter to the report program'],
		['Enter', 'Open the report'],
		['/', 'Search'],
		['?', 'Keyboard shortcuts'],
		['Esc', 'Collapse the report']
	];

	function toggle(id: string) {
		if (expanded.has(id)) expanded.delete(id);
		else expanded.add(id);
	}
</script>

<svelte:head><title>{pageTitle(`${label} · ${routeLabels['bounty-hub']}`)}</title></svelte:head>
<svelte:window onkeydown={onKey} />

{#snippet sortHead(text: string, key: ReportSort, cls: string)}
	<button
		type="button"
		class="{cls} items-center gap-1 text-left tracking-wide uppercase hover:text-foreground {filters.sort ===
		key
			? 'text-foreground'
			: ''}"
		onclick={() => sortBy(key)}
	>
		{text}
		{#if filters.sort === key}
			{#if filters.order === 'desc'}<ArrowDown class="size-3" />{:else}<ArrowUp
					class="size-3"
				/>{/if}
		{/if}
	</button>
{/snippet}

{#snippet stat(title: string, value: string, sub: string, tab: string | null)}
	{@const on = tab !== null && filters.tab === tab && tab !== ALL_TAB}
	<button
		type="button"
		class="group/s flex flex-col items-start gap-0.5 rounded-md text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
		aria-pressed={on}
		onclick={() => tab !== null && setParam('tab', on || tab === ALL_TAB ? null : tab)}
	>
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">{title}</span>
		<span
			class="font-mono text-2xl font-semibold tabular-nums underline-offset-4 group-hover/s:text-primary {on
				? 'underline decoration-2'
				: ''}"
		>
			{value}
		</span>
		{#if sub}<span class="text-2xs text-muted-foreground">{sub}</span>{/if}
	</button>
{/snippet}

<div class="flex flex-col gap-4">
	<h1 class="sr-only">{label}</h1>

	{#if spec && !spec.tracks_reports}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<EmptyState
				title="{label} has no report API"
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" href={ROUTES.bountyHub()}>
					{routeLabels['bounty-hub']}
				</Button>
			</EmptyState>
		</Card.Root>
	{:else if accountFailed}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<EmptyState
				icon={TriangleAlert}
				title="Reports not loaded"
				description={accountFailed}
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={() => loadAccount(platform)}>Retry</Button>
			</EmptyState>
		</Card.Root>
	{:else if connected === false}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<EmptyState
				icon={KeyRound}
				title="{label} not connected"
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button size="sm" href={ROUTES.settings('api-keys')}>
					<KeyRound class="size-4" />
					Add API key
				</Button>
			</EmptyState>
		</Card.Root>
	{:else}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<!-- account -->
			<div
				class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-muted/10 px-4 py-2.5"
			>
				<div
					class="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground"
				>
					<span class="text-sm font-semibold text-foreground">{label}</span>
					{#if summary?.username}
						<a
							href={externalHref(`${platformUrl}/${summary.username}`)}
							target="_blank"
							rel="noopener noreferrer"
							class="flex items-center gap-0.5 font-mono text-foreground hover:text-primary"
						>
							@{summary.username}<ArrowUpRight class="size-3" />
						</a>
					{/if}
					{#if summary?.reputation != null}
						<span>
							Reputation
							<span class="font-mono font-medium text-foreground tabular-nums"
								>{summary.reputation}</span
							>
						</span>
					{/if}
					{#if summary?.signal != null}
						<span>
							Signal
							<span class="font-mono font-medium text-foreground tabular-nums"
								>{summary.signal.toFixed(2)}</span
							>
						</span>
					{/if}
					{#if summary?.impact != null}
						<span>
							Impact
							<span class="font-mono font-medium text-foreground tabular-nums"
								>{summary.impact.toFixed(2)}</span
							>
						</span>
					{/if}
					{#if summary?.synced_at}
						<Hint text={formatShortDate(summary.synced_at)}>
							{#snippet child(props)}
								<span {...props}>Synced {relativeTime(summary?.synced_at)}</span>
							{/snippet}
						</Hint>
					{/if}
				</div>
				<Hint text={isAdmin ? 'Refresh reports' : 'Refreshed by administrators'}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<Button
								variant="outline"
								size="icon-sm"
								aria-label="Refresh reports"
								disabled={refreshing || !isAdmin}
								onclick={() => refresh()}
							>
								<RefreshCw class="size-4 {refreshing ? 'animate-spin' : ''}" />
							</Button>
						</span>
					{/snippet}
				</Hint>
			</div>

			{#if summary?.error}
				<div
					class="flex items-center gap-2 border-b bg-destructive/5 px-4 py-2 text-xs text-destructive"
				>
					<TriangleAlert class="size-3.5 shrink-0" /> Reports not refreshed. {summary.error}
				</div>
			{/if}

			<!-- strip -->
			<div class="grid gap-x-8 gap-y-4 border-b px-4 py-4 xl:grid-cols-[auto_minmax(18rem,1fr)]">
				{#if !summary}
					<div class="flex flex-wrap gap-x-8 gap-y-3" aria-busy="true">
						{#each ['w-16', 'w-14', 'w-16', 'w-24'] as w, i (i)}
							<div class="flex flex-col gap-1.5">
								<Skeleton class="h-3 {w}" />
								<Skeleton class="h-7 w-14" />
							</div>
						{/each}
					</div>
					<Skeleton class="h-14 w-full" />
				{:else}
					<div class="flex flex-wrap items-start gap-x-8 gap-y-3">
						{@render stat(
							'Earned',
							summary.earned.length ? formatMonies(summary.earned) : '0',
							`${payments} ${payments === 1 ? 'payment' : 'payments'} on ${summary.paid_reports} ${summary.paid_reports === 1 ? 'report' : 'reports'}`,
							PAID_TAB
						)}
						{@render stat(
							'Reports',
							String(summary.reports),
							`${summary.programs} programs`,
							ALL_TAB
						)}
						{@render stat(
							'Resolved',
							String(summary.stages.resolved ?? 0),
							`${resolvedShare}% of reports`,
							'resolved'
						)}
						{@render stat(
							'Open',
							String(summary.stages.open ?? 0),
							summary.last_submitted_at
								? `Last submitted ${formatShortDate(summary.last_submitted_at)}`
								: '',
							'open'
						)}
						<div class="flex flex-col gap-1">
							<span class="text-2xs tracking-wide text-muted-foreground uppercase">Severity</span>
							<div class="flex flex-wrap items-center gap-1.5">
								{#each summary.severities as s (s.severity)}
									{@const key = REPORT_SEVERITY_KEY[s.severity] ?? s.severity}
									{@const on = filters.severities.includes(s.severity)}
									<button
										type="button"
										class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 font-mono text-sm font-semibold tabular-nums transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {SEVERITY_CHIP[
											key
										]?.chip ?? ''} {on ? 'ring-2 ring-current/50' : ''}"
										aria-pressed={on}
										aria-label="{severityLabel(s.severity)} reports: {s.count}"
										onclick={() => toggleIn('severity', s.severity, filters.severities)}
									>
										<span class="text-2xs font-medium opacity-70">{severityLabel(s.severity)}</span>
										{s.count}
									</button>
								{/each}
							</div>
						</div>
					</div>
					{#if summary.monthly.length}<MonthChart
							months={summary.monthly}
							currency={summary.chart_currency}
							from={filters.from}
							to={filters.to}
							onRange={(f, t) =>
								update((s) => {
									if (f) s.set('from', f);
									else s.delete('from');
									if (t) s.set('to', t);
									else s.delete('to');
								})}
						/>{/if}
				{/if}
			</div>

			<!-- tabs -->
			<div class="flex flex-wrap items-center justify-between gap-2 border-b px-2">
				{#if view === ReportView.Reports}
					<CountTabs
						{tabs}
						value={filters.tab}
						{counts}
						countClass={(k, n) =>
							n === 0
								? 'text-muted-foreground/50'
								: k === 'open'
									? 'text-info'
									: 'text-muted-foreground'}
						onChange={(k) => setParam('tab', k === ALL_TAB ? null : k)}
					/>
				{:else}
					<CountTabs
						tabs={[{ key: 'programs', label: 'Programs' }]}
						value="programs"
						counts={{ programs: programs.length }}
					/>
				{/if}
				<ToggleGroup.Root
					type="single"
					variant="outline"
					size="sm"
					value={view}
					onValueChange={(v) => v && setParam('view', v === ReportView.Reports ? null : v)}
					aria-label="View"
					class="my-1.5"
				>
					<ToggleGroup.Item value={ReportView.Reports} class="px-3 text-xs"
						>Reports</ToggleGroup.Item
					>
					<ToggleGroup.Item value={ReportView.Programs} class="px-3 text-xs"
						>By program</ToggleGroup.Item
					>
				</ToggleGroup.Root>
			</div>

			<!-- filters -->
			<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
				<InputGroup.Root class="h-9 w-auto min-w-[240px] flex-1">
					<InputGroup.Addon>
						<Search />
					</InputGroup.Addon>
					<InputGroup.Input
						bind:ref={searchEl}
						placeholder={view === ReportView.Reports
							? 'Title, report ID, program, weakness or asset'
							: 'Program name or handle'}
						value={view === ReportView.Reports ? queryText : programQuery}
						oninput={(e) => {
							if (view === ReportView.Reports) queryText = e.currentTarget.value;
							else programQuery = e.currentTarget.value;
						}}
						onkeydown={(e) => {
							if (e.key === 'Enter' && view === ReportView.Reports) search(queryText);
							if (e.key === 'Escape') e.currentTarget.blur();
						}}
						aria-label="Search reports"
					/>
					<InputGroup.Addon align="inline-end">
						{#if view === ReportView.Reports ? queryText : programQuery}
							<InputGroup.Button
								size="icon-xs"
								aria-label="Clear search"
								onclick={() => (view === ReportView.Reports ? search('') : (programQuery = ''))}
							>
								<X />
							</InputGroup.Button>
						{:else}
							<Kbd class="hidden sm:inline-flex">/</Kbd>
						{/if}
					</InputGroup.Addon>
				</InputGroup.Root>
				{#if view === ReportView.Reports}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button {...props} variant="outline">
									Program
									{#if filters.programs.length}
										<span class="font-mono text-2xs text-muted-foreground"
											>{filters.programs.length}</span
										>
									{/if}
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="max-h-none w-64 overflow-visible p-0">
							<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
								<div class="p-1">
									{#each programs as p (p.handle)}
										<DropdownMenu.CheckboxItem
											checked={filters.programs.includes(p.handle)}
											onCheckedChange={() => toggleIn('program', p.handle, filters.programs)}
											closeOnSelect={false}
										>
											<span class="flex-1 truncate">{p.name}</span>
											<span class="font-mono text-2xs text-muted-foreground">{p.reports}</span>
										</DropdownMenu.CheckboxItem>
									{/each}
								</div>
							</ScrollArea>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button {...props} variant="outline">
									State
									{#if filters.states.length}
										<span class="font-mono text-2xs text-muted-foreground"
											>{filters.states.length}</span
										>
									{/if}
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="w-56">
							{#each summary?.states ?? [] as s (s.state)}
								<DropdownMenu.CheckboxItem
									checked={filters.states.includes(s.state)}
									onCheckedChange={() => toggleIn('state', s.state, filters.states)}
									closeOnSelect={false}
								>
									<span class="flex-1">{s.label}</span>
									<span class="font-mono text-2xs text-muted-foreground">{s.count}</span>
								</DropdownMenu.CheckboxItem>
							{/each}
						</DropdownMenu.Content>
					</DropdownMenu.Root>
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button {...props} variant="outline" size="icon" aria-label="Density">
									<Rows3 class="size-4" />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="w-44">
							<DropdownMenu.RadioGroup
								value={compact ? 'compact' : 'comfortable'}
								onValueChange={(v) => (compact = v === 'compact')}
							>
								<DropdownMenu.RadioItem value="comfortable">Comfortable</DropdownMenu.RadioItem>
								<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
							</DropdownMenu.RadioGroup>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
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
				{/if}
			</div>

			<!-- saved views and active filters -->
			{#if view === ReportView.Reports}
				<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
					{#each REPORT_SAVED_VIEWS as v (v.label)}
						{@const on = savedOn(v)}
						<button
							type="button"
							class="rounded-full border px-2.5 py-0.5 text-xs transition-colors {on
								? 'border-foreground/40 bg-foreground text-background'
								: 'border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground'}"
							aria-pressed={on}
							onclick={() => applyView(v)}
						>
							{v.label}
						</button>
					{/each}
					{#snippet chip(text: string, onRemove: () => void)}
						<span
							class="inline-flex items-center gap-1 rounded-full border border-border bg-background px-2 py-0.5 text-xs"
						>
							{text}
							<button
								type="button"
								aria-label="Remove {text}"
								class="text-muted-foreground hover:text-foreground"
								onclick={onRemove}
							>
								<X class="size-3" />
							</button>
						</span>
					{/snippet}
					{#if hasFilters}<span class="mx-1 h-4 w-px bg-border"></span>{/if}
					{#each filters.programs as h (h)}
						{@render chip(programName(h), () =>
							setList(
								'program',
								filters.programs.filter((x) => x !== h)
							)
						)}
					{/each}
					{#each filters.states as st (st)}
						{@render chip(stateLabel(st), () =>
							setList(
								'state',
								filters.states.filter((x) => x !== st)
							)
						)}
					{/each}
					{#each filters.severities as sv (sv)}
						{@render chip(severityLabel(sv), () =>
							setList(
								'severity',
								filters.severities.filter((x) => x !== sv)
							)
						)}
					{/each}
					{#if filters.q}
						{@render chip(`“${filters.q}”`, () => search(''))}
					{/if}
					{#if filters.from}
						{@render chip(
							filters.to
								? `Submitted ${formatShortDate(filters.from, true)} to ${formatShortDate(new Date(new Date(filters.to).getTime() - 1), true)}`
								: `Submitted from ${formatShortDate(filters.from, true)}`,
							() =>
								update((s) => {
									s.delete('from');
									s.delete('to');
								})
						)}
					{/if}
					{#if hasFilters}
						<button
							type="button"
							class="ml-auto text-xs text-muted-foreground hover:text-foreground"
							onclick={clearFilters}
						>
							Clear all
						</button>
					{/if}
				</div>
			{/if}

			{#if view === ReportView.Programs}
				{#if programs.length === 0}
					<EmptyState title="No programs" compact class="border-0 bg-transparent py-16" />
				{:else}
					<ProgramsTable
						{programs}
						{platform}
						{platformUrl}
						query={programQuery}
						onOpen={onlyProgram}
					/>
				{/if}
			{:else if loading && reports.length === 0}
				<TableSkeleton
					lead={[{ key: 'name', label: 'Report', width: 'min-w-0 flex-1' }]}
					actions={false}
				/>
			{:else if failed && reports.length === 0}
				<EmptyState
					icon={TriangleAlert}
					title="Reports not loaded"
					description={failed}
					compact
					class="border-0 bg-transparent py-16"
				>
					<Button
						size="sm"
						variant="outline"
						onclick={() => loadList(platform, filters, pageIndex, pageSize)}
					>
						Retry
					</Button>
				</EmptyState>
			{:else if reports.length === 0 && (hasFilters || filters.tab !== ALL_TAB)}
				<EmptyState title="No reports match" compact class="border-0 bg-transparent py-16">
					<Button size="sm" variant="outline" onclick={clearFilters}>
						<X class="size-4" />
						Clear filters
					</Button>
				</EmptyState>
			{:else if reports.length === 0}
				<EmptyState
					icon={FileText}
					title="No reports"
					compact
					class="border-0 bg-transparent py-16"
				>
					<Hint text={isAdmin ? null : 'Refreshed by administrators'}>
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<Button size="sm" onclick={() => refresh()} disabled={refreshing || !isAdmin}>
									<RefreshCw class="size-4" />
									Refresh reports
								</Button>
							</span>
						{/snippet}
					</Hint>
				</EmptyState>
			{:else}
				<ScrollArea orientation="horizontal">
					<div
						class="w-full min-w-[720px] {loading ? 'opacity-60' : ''}"
						role="table"
						aria-label="Reports"
					>
						<div
							class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
							role="row"
						>
							<div class={RCOL.report}>Report</div>
							{@render sortHead('Program', ReportSort.Program, RCOL.program)}
							{@render sortHead('Severity', ReportSort.Severity, `${RCOL.severity} flex`)}
							<div class={RCOL.state}>State</div>
							{@render sortHead('Bounty', ReportSort.Bounty, RCOL.bounty)}
							{@render sortHead('Submitted', ReportSort.Submitted, RCOL.submitted)}
							<div class={RCOL.actions}></div>
						</div>
						{#each reports as r (r.id)}
							<ReportRow
								report={r}
								program={r.program_handle ? programMap.get(r.program_handle) : undefined}
								platformLabel={label}
								{platformUrl}
								expanded={expanded.has(r.id)}
								focused={focusId === r.id}
								{compact}
								onToggle={() => toggle(r.id)}
								onProgram={onlyProgram}
								onSearch={search}
							/>
						{/each}
					</div>
				</ScrollArea>
				<ResultsPagination
					page={pageIndex - 1}
					{pageSize}
					{total}
					noun="report"
					sizes={REPORT_PAGE_SIZES}
					onPage={(p) => setParam('page', String(p + 1), true)}
					onPageSize={(s) => setParam('size', String(s))}
				/>
			{/if}
		</Card.Root>
	{/if}
</div>

<Dialog.Root bind:open={shortcutsOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header><Dialog.Title>Keyboard shortcuts</Dialog.Title></Dialog.Header>
		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
			{#each SHORTCUTS as [key, action] (key)}
				<dt><Kbd>{key}</Kbd></dt>
				<dd class="text-muted-foreground">{action}</dd>
			{/each}
		</dl>
	</Dialog.Content>
</Dialog.Root>
