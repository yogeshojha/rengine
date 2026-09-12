<script lang="ts">
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import Bug from '@lucide/svelte/icons/bug';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import SearchX from '@lucide/svelte/icons/search-x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Toggle } from '$lib/components/ui/toggle';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SearchBar from '$lib/components/search-bar.svelte';
	import FindingsTabs from '$lib/components/surface/findings-tabs.svelte';
	import CveRow from '$lib/components/cve/cve-row.svelte';
	import {
		CVE_COLUMNS,
		CVE_FILTERS,
		CVE_LEAD_COLUMNS,
		CVE_SORTS
	} from '$lib/components/cve/columns';
	import ListHeader from '$lib/components/scans/results/table/list-header.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import SortMenu from '$lib/components/scans/results/table/sort-menu.svelte';
	import { cvesApi } from '$lib/api/cves';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { EVIDENCE_ORDER } from '$lib/config/evidence';
	import { SEVERITY_LABELS, SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import type { CveIndex, CveIndexRow } from '$lib/types/cve';

	const CVE_ID = /^CVE-\d{4}-\d{4,7}$/i;
	const SEVERITY_TABS = [
		{ key: 'all', label: 'All' },
		...SEVERITY_ORDER.filter((k) => k !== 'unknown' && k !== 'info').map((k) => ({
			key: k,
			label: SEVERITY_LABELS[k]
		}))
	];

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let query = $state('');
	let severity = $state('all');
	let active = $state<string[]>([]);
	let sort = $state<{ key: string; dir: 1 | -1 }>({ key: 'rank', dir: -1 });
	let pageIndex = $state(0);
	let pageSize = $state(50);

	let index = $state<CveIndex | null>(null);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let searchRef = $state<HTMLInputElement | null>(null);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let reqId = 0;

	async function load(id: string) {
		const mine = ++reqId;
		if (index) refreshing = true;
		else loading = true;
		try {
			const data = await cvesApi.index(id, {
				q: query.trim(),
				page: pageIndex + 1,
				size: pageSize,
				sort: sort.key,
				dir: sort.dir === 1 ? 'asc' : 'desc',
				severity: severity === 'all' ? null : severity,
				kev: active.includes('kev'),
				ransomware: active.includes('ransomware'),
				evidence: active.filter((k) => EVIDENCE_ORDER.includes(k))
			});
			if (mine !== reqId) return;
			index = data;
			errored = false;
		} catch {
			if (mine !== reqId) return;
			errored = true;
		} finally {
			if (mine === reqId) {
				loading = false;
				refreshing = false;
			}
		}
	}

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void load(id));
	});

	function rerun() {
		if (projectId) void load(projectId);
	}

	function onQuery(value: string) {
		query = value;
		pageIndex = 0;
		if (timer) clearTimeout(timer);
		timer = setTimeout(rerun, SEARCH_DEBOUNCE_MS);
	}

	function onSubmit(value: string) {
		const cve = value.trim().toUpperCase();
		if (CVE_ID.test(cve)) void goto(ROUTES.cve(cve));
	}

	function setSeverity(key: string) {
		severity = key;
		pageIndex = 0;
		rerun();
	}

	function toggle(key: string) {
		active = active.includes(key) ? active.filter((k) => k !== key) : [...active, key];
		pageIndex = 0;
		rerun();
	}

	function onSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: -1 };
		pageIndex = 0;
		rerun();
	}

	function onPage(next: number) {
		pageIndex = Math.max(0, Math.min(next, pageCount - 1));
		rerun();
	}

	function clearFilters() {
		query = '';
		severity = 'all';
		active = [];
		pageIndex = 0;
		rerun();
	}

	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		const typing =
			!!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
		if (e.key === '/' && !typing) {
			e.preventDefault();
			searchRef?.focus();
		}
	}

	let items = $derived(index?.items ?? []);
	let total = $derived(index?.total ?? 0);
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let filtered = $derived(Boolean(query.trim()) || severity !== 'all' || active.length > 0);
	let term = $derived(query.trim());
	let severityCounts = $derived.by(() => {
		const out: Record<string, number> = { all: index?.matched ?? 0 };
		for (const [key, n] of Object.entries(index?.severity_counts ?? {})) out[key] = n;
		return out;
	});
	let coverageLine = $derived(
		index
			? [
					`${index.software_scans.toLocaleString()} ${index.software_scans === 1 ? 'target' : 'targets'} with software inference`,
					`${index.finding_scans.toLocaleString()} ${index.finding_scans === 1 ? 'target' : 'targets'} with checks`
				].join(' · ')
			: ''
	);
</script>

<svelte:window onkeydown={onKey} />

<div class="space-y-6">
	<FindingsTabs value="cve" />

	<div class="overflow-hidden rounded-xl border bg-card">
		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2 text-xs">
			<Bug class="size-3.5 shrink-0 text-muted-foreground" />
			<span class="text-muted-foreground">{coverageLine}</span>
		</div>
	</div>

	{#if index && !index.corpus_ready}
		<Alert.Alert>
			<Alert.AlertTitle>Software inference not available</Alert.AlertTitle>
			<Alert.AlertDescription>
				The NVD corpus is not loaded. Only CVEs a check reported are listed.
			</Alert.AlertDescription>
		</Alert.Alert>
	{/if}

	<div>
		<SearchBar
			bind:ref={searchRef}
			value={query}
			mono
			label="Search CVEs"
			placeholder="CVE-2021-44228"
			busy={refreshing}
			total={errored ? null : total}
			noun="CVE"
			nounPlural="CVEs"
			onChange={onQuery}
			{onSubmit}
		/>

		<Card.Root class="gap-0 overflow-hidden rounded-t-none border-t-0 py-0">
			<div class="flex items-center gap-3 border-b pr-3 pl-2">
				<div class="min-w-0 flex-1">
					<CountTabs
						tabs={SEVERITY_TABS}
						value={severity}
						counts={severityCounts}
						onChange={setSeverity}
					/>
				</div>
			</div>

			<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
				{#each CVE_FILTERS as filter (filter.key)}
					<Toggle
						size="sm"
						variant="outline"
						pressed={active.includes(filter.key)}
						onPressedChange={() => toggle(filter.key)}
						class="h-7 px-2.5 text-xs font-normal"
					>
						{filter.label}
					</Toggle>
				{/each}
				<div class="ml-auto flex items-center gap-1.5">
					<SortMenu sorts={CVE_SORTS} sortKey={sort.key} sortDir={sort.dir} {onSort} />
					<Button variant="ghost" size="icon" class="size-7" aria-label="Refresh" onclick={rerun}>
						<RefreshCw class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
					</Button>
				</div>
			</div>

			{#if loading}
				<div class="flex flex-col gap-2 px-4 py-4">
					{#each Array(6) as _, i (i)}
						<Skeleton class="h-10 w-full" />
					{/each}
				</div>
			{:else if errored}
				<EmptyState icon={TriangleAlert} title="CVEs not loaded">
					<Button variant="outline" size="sm" onclick={rerun}>Retry</Button>
				</EmptyState>
			{:else if items.length === 0}
				<EmptyState
					icon={filtered ? SearchX : Bug}
					title={filtered ? 'No CVE matches' : 'No CVE in this project'}
				>
					{#if filtered}
						<Button variant="outline" size="sm" onclick={clearFilters}>Clear filters</Button>
					{/if}
				</EmptyState>
			{:else}
				<ScrollArea orientation="horizontal" class="min-h-0">
					<div class="min-w-max">
						<ListHeader
							lead={CVE_LEAD_COLUMNS}
							columns={CVE_COLUMNS}
							sortKey={sort.key}
							sortDir={sort.dir}
							{onSort}
						/>
						<div
							class="divide-y divide-border/50 transition-opacity {refreshing ? 'opacity-60' : ''}"
						>
							{#each items as row (row.cve)}
								<CveRow
									{row}
									{term}
									columns={CVE_COLUMNS}
									pad="py-3"
									onOpen={(r: CveIndexRow) => goto(ROUTES.cve(r.cve))}
								/>
							{/each}
						</div>
					</div>
				</ScrollArea>

				<ResultsPagination
					{total}
					page={pageIndex}
					{pageSize}
					noun="CVE"
					plural="CVEs"
					{onPage}
					onPageSize={(size) => {
						pageSize = size;
						pageIndex = 0;
						rerun();
					}}
				/>
			{/if}
		</Card.Root>
	</div>
</div>
