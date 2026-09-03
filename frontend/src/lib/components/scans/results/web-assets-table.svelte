<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import Star from '@lucide/svelte/icons/star';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Link from '@lucide/svelte/icons/link';
	import Filter from '@lucide/svelte/icons/filter';
	import CornerDownRight from '@lucide/svelte/icons/corner-down-right';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Globe from '@lucide/svelte/icons/globe';

	import * as Table from '$lib/components/ui/table';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';

	import SearchBar from './web-assets/search-bar.svelte';
	import FilterBar, { type ColumnDef } from './web-assets/filter-bar.svelte';
	import OverflowPopover from './web-assets/overflow-popover.svelte';
	import HostHoverCard from './web-assets/host-hover-card.svelte';
	import AssetGallery from './web-assets/asset-gallery.svelte';
	import ResultsPagination from './web-assets/results-pagination.svelte';
	import SamePagePopover from './web-assets/same-page-popover.svelte';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechIcon from './tech-icon.svelte';
	import WebAssetDetailSheet from './web-asset-detail-sheet.svelte';

	import { subdomainsApi } from '$lib/api/subdomains';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import {
		providerFor,
		PROVIDER_KIND_ICONS,
		PROVIDER_KIND_LABELS
	} from '$lib/config/hosting-providers';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusClass,
		httpStatusReason,
		httpStatusTextClass,
		isSensitivePort,
		STATUS_DOT
	} from '$lib/utilities/scan-correlation';
	import {
		appendToken,
		exactToken,
		certState,
		daysUntilExpiry,
		activeFacetCount,
		emptyQuery,
		compileQuery,
		DSL_KEYS,
		type WebAssetQuery,
		type SubdomainFacetSet
	} from '$lib/utilities/scan-insights';
	import {
		RESULTS_PAGE_SIZE,
		SEARCH_DEBOUNCE_MS,
		RESULTS_SCROLL
	} from '$lib/utilities/scan-status';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
		query?: WebAssetQuery;
	}

	let { scanId, projectId, active = true, query = $bindable(emptyQuery()) }: Props = $props();

	interface Column extends ColumnDef {
		sort?: string;
		align?: 'right';
		width?: string;
	}
	const COLUMNS: Column[] = [
		{ key: 'screenshot', label: 'Screenshot', width: 'w-20' },
		{ key: 'status', label: 'Status', sort: 'status', width: 'w-24' },
		{ key: 'title', label: 'Title', sort: 'title' },
		{ key: 'tech', label: 'Tech' },
		{ key: 'ip', label: 'IP / CDN', sort: 'ip' },
		{ key: 'ports', label: 'Ports' },
		{ key: 'cert', label: 'Cert', sort: 'cert', width: 'w-24' },
		{ key: 'waf', label: 'WAF' },
		{ key: 'asn', label: 'Network' },
		{ key: 'sources', label: 'Sources' },
		{ key: 'discovered', label: 'Found', sort: 'discovered', width: 'w-24' },
		{ key: 'size', label: 'Size', sort: 'size', align: 'right', width: 'w-20' },
		{ key: 'time', label: 'Time', sort: 'time', align: 'right', width: 'w-20' }
	];
	const DEFAULT_VISIBLE = ['status', 'title', 'tech', 'ip', 'ports', 'cert', 'size', 'time'];
	const DEFAULT_SORT = { key: 'status', dir: 1 as const };
	const EMPTY_FACETS: SubdomainFacetSet = {
		status: [],
		tech: [],
		service: [],
		source: [],
		cert: []
	};
	const MAX_TECH = 2;
	const MAX_PORTS = 3;
	const MAX_SOURCES = 2;

	function readPref<T>(key: string, fallback: T): T {
		try {
			const raw = localStorage.getItem(key);
			return raw ? (JSON.parse(raw) as T) : fallback;
		} catch {
			return fallback;
		}
	}
	function writePref(key: string, value: unknown) {
		try {
			localStorage.setItem(key, JSON.stringify(value));
		} catch {
			// storage is a convenience
		}
	}

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('sort')?.split(':') ?? [];
	let pendingAsset = initial.get('asset');

	let visible = $state<string[]>(readPref(STORAGE_KEYS.webAssetsColumns, DEFAULT_VISIBLE));
	let view = $state<string>(initial.get('view') === 'gallery' ? 'gallery' : 'table');
	let density = $state<string>(readPref(STORAGE_KEYS.webAssetsDensity, 'compact'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.webAssetsPageSize, RESULTS_PAGE_SIZE));
	let onlyShots = $state(true);
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('page') ?? 1) - 1));

	let items = $state<SubdomainRead[]>([]);
	let total = $state(0);
	let loading = $state(true);
	let errored = $state(false);
	let facets = $state<SubdomainFacetSet>(EMPTY_FACETS);

	let selected = $state<SubdomainRead | null>(null);
	let drawerOpen = $state(false);
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;

	let scanTotal = $derived(facets.status.reduce((n, f) => n + f.count, 0));
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let selectedIndex = $derived(selected ? items.findIndex((s) => s.id === selected?.id) : -1);
	let shownColumns = $derived(COLUMNS.filter((c) => visible.includes(c.key)));
	let filtered = $derived(activeFacetCount(query) > 0 || !!query.search);
	let stripe = $derived(
		density === 'compact'
			? '[&_td]:h-12 [&_td]:py-2 [&_td]:align-top'
			: '[&_td]:h-16 [&_td]:py-3.5 [&_td]:align-top'
	);

	$effect(() => writePref(STORAGE_KEYS.webAssetsColumns, visible));
	$effect(() => writePref(STORAGE_KEYS.webAssetsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.webAssetsPageSize, pageSize));

	const initialSearch = initial.get('q');
	if (initialSearch) query = { ...query, search: initialSearch };

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let lastSig = '';

	async function runSearch() {
		const q = view === 'gallery' && onlyShots ? { ...query, hasScreenshot: true } : query;
		const filter = compileQuery(q, sort.key, sort.dir, pageIndex * pageSize, pageSize);
		const sig = JSON.stringify({ ...filter, offset: 0 });
		if (sig !== lastSig && pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			pageIndex = 0;
			return;
		}
		lastSig = sig;
		const my = ++reqId;
		loading = true;
		try {
			const res = await subdomainsApi.search(projectId, scanId, filter);
			if (my !== reqId) return;
			items = res.items;
			total = res.total;
			errored = false;
			if (pendingSelect) {
				selected = pendingSelect === 'first' ? (items[0] ?? null) : (items.at(-1) ?? null);
				pendingSelect = null;
			} else if (pendingAsset) {
				const name = pendingAsset;
				pendingAsset = null;
				const hit = items.find((s) => s.name === name);
				if (hit) open(hit);
				else openHost(name);
			}
		} catch {
			if (my === reqId) {
				items = [];
				total = 0;
				errored = true;
			}
		} finally {
			if (my === reqId) loading = false;
		}
	}

	$effect(() => {
		void JSON.stringify(query);
		void sort.key;
		void sort.dir;
		void pageIndex;
		void pageSize;
		void view;
		void onlyShots;
		void scanId;
		void projectId;
		if (!seen) return;
		if (timer) clearTimeout(timer);
		timer = setTimeout(runSearch, SEARCH_DEBOUNCE_MS);
		return () => {
			if (timer) clearTimeout(timer);
		};
	});

	$effect(() => {
		const id = scanId;
		const pid = projectId;
		if (!id || !pid || !seen) return;
		subdomainsApi
			.facets(pid, id)
			.then((f) => (facets = f))
			.catch(() => (facets = EMPTY_FACETS));
	});

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams(location.search);
			const set = (k: string, v: string | null) => (v ? sp.set(k, v) : sp.delete(k));
			set('q', query.search || null);
			set('view', view === 'gallery' ? 'gallery' : null);
			set('page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set(
				'sort',
				sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir
					? `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`
					: null
			);
			set('asset', drawerOpen && selected ? selected.name : null);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// URL state is best-effort
		}
	}
	$effect(() => {
		void query.search;
		void view;
		void pageIndex;
		void sort.key;
		void sort.dir;
		void drawerOpen;
		void selected?.name;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(s: SubdomainRead) {
		selected = s;
		drawerOpen = true;
	}
	async function openHost(name: string) {
		const hit = items.find((s) => s.name === name);
		if (hit) return open(hit);
		try {
			const res = await subdomainsApi.search(
				projectId,
				scanId,
				compileQuery({ ...emptyQuery(), search: `name:${name}` }, 'name', 1, 0, 5)
			);
			const exact = res.items.find((s) => s.name === name);
			if (exact) open(exact);
			else toast.error('Host not found in this scan');
		} catch {
			toast.error('Could not load host');
		}
	}
	function step(dir: -1 | 1) {
		const next = selectedIndex + dir;
		if (next >= 0 && next < items.length) {
			selected = items[next];
			return;
		}
		if (dir === 1 && pageIndex < pageCount - 1) {
			pendingSelect = 'first';
			pageIndex += 1;
		} else if (dir === -1 && pageIndex > 0) {
			pendingSelect = 'last';
			pageIndex -= 1;
		}
	}
	function toggleSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: 1 };
		pageIndex = 0;
	}
	function toggleCol(key: string) {
		visible = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: WebAssetQuery) {
		query = q;
		pageIndex = 0;
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function hostsWithTitle(title: string): Promise<string[]> {
		return subdomainsApi
			.search(
				projectId,
				scanId,
				compileQuery({ ...emptyQuery(), search: exactToken('title', title) }, 'name', 1, 0, 50)
			)
			.then((r) => r.items.map((i) => i.name));
	}
	async function copy(text: string, label = 'Copied') {
		if (await writeClipboard(text)) toast.success(label);
	}
	function scrollCursor() {
		document.querySelector(`[data-row-index="${cursor}"]`)?.scrollIntoView({ block: 'nearest' });
	}
	function onKey(e: KeyboardEvent) {
		if (!active || e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		const typing =
			!!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
		if (e.key === '/' && !typing) {
			e.preventDefault();
			searchRef?.focus();
			return;
		}
		if (typing || drawerOpen || view !== 'table' || !items.length) return;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			cursor = Math.min(cursor + 1, items.length - 1);
			scrollCursor();
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			cursor = Math.max(cursor - 1, 0);
			scrollCursor();
		} else if (e.key === 'Enter' && cursor >= 0 && items[cursor]) {
			open(items[cursor]);
		} else if (e.key === 'Escape') {
			cursor = -1;
		}
	}
	const stop = (e: Event) => e.stopPropagation();
</script>

<svelte:window onkeydown={onKey} />

<div class="flex flex-col gap-3">
	<div class="mx-auto w-full max-w-3xl">
		<SearchBar
			bind:ref={searchRef}
			value={query.search}
			keys={DSL_KEYS}
			values={facets}
			placeholder="Search hosts, titles, IPs — or filter with status:2xx tech:nginx is:live"
			onChange={(v) => setQuery({ ...query, search: v })}
		/>
	</div>

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		{total}
		{scanTotal}
		{view}
		onView={(v) => {
			view = v;
			pageIndex = 0;
		}}
		columns={COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
		{onlyShots}
		onOnlyShots={(v) => {
			onlyShots = v;
			pageIndex = 0;
		}}
	/>

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-2">
			{#each Array(8) as _, i (i)}
				<Skeleton class="h-12 w-full" />
			{/each}
		</div>
	{:else if errored}
		<EmptyState icon={TriangleAlert} title="Web assets could not be loaded">
			<Button size="sm" variant="outline" onclick={runSearch}>Retry</Button>
		</EmptyState>
	{:else if items.length === 0}
		{#if filtered || (view === 'gallery' && onlyShots)}
			<EmptyState
				icon={SearchX}
				title="No hosts match"
				description="Widen the search or remove a filter."
			>
				<Button size="sm" variant="outline" onclick={() => setQuery(emptyQuery())}>
					Clear filters
				</Button>
			</EmptyState>
		{:else}
			<EmptyState
				icon={Globe}
				title="No web assets yet"
				description="Hosts appear here as subdomain discovery and HTTP probing complete."
			/>
		{/if}
	{:else if view === 'gallery'}
		<AssetGallery
			{items}
			{loading}
			selectedId={drawerOpen ? (selected?.id ?? null) : null}
			onOpen={open}
		/>
	{:else}
		<div class="overflow-hidden rounded-lg border transition-opacity {loading ? 'opacity-60' : ''}">
			<Table.Root containerClass={RESULTS_SCROLL}>
				<Table.Header class="sticky top-0 z-20 bg-background">
					<Table.Row class="hover:bg-transparent">
						<Table.Head class="sticky left-0 z-30 min-w-56 bg-background">
							{@render sortHead('Host', 'name')}
						</Table.Head>
						{#each shownColumns as col (col.key)}
							<Table.Head class="{col.width ?? ''} {col.align === 'right' ? 'text-right' : ''}">
								{#if col.sort}
									{@render sortHead(col.label, col.sort)}
								{:else}
									{col.label}
								{/if}
							</Table.Head>
						{/each}
						<Table.Head class="w-16"></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body class={stripe}>
					{#each items as s, i (s.id)}
						{@const cert = certState(s)}
						{@const ports = s.ports ?? []}
						{@const ips = s.resolved_ips ?? []}
						{@const isSelected = drawerOpen && selected?.id === s.id}
						{@const redirected = !!s.final_url && s.final_url !== s.http_url}
						<Table.Row
							class="group cursor-pointer {cursor === i ? 'bg-muted/40' : ''}"
							data-state={isSelected ? 'selected' : undefined}
							data-row-index={i}
							role="button"
							tabindex={0}
							onclick={() => open(s)}
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									open(s);
								}
							}}
						>
							<Table.Cell
								class="sticky left-0 z-10 bg-background group-hover:bg-[color-mix(in_oklab,var(--muted)_50%,var(--background))] group-data-[state=selected]:bg-muted"
							>
								<div class="flex items-center gap-1.5">
									{#if s.is_important}
										<Star class="size-3 shrink-0 fill-warning text-warning" />
									{/if}
									<HostHoverCard sub={s}>
										<span
											class="font-mono text-xs font-medium {s.is_active
												? ''
												: 'text-muted-foreground'}">{s.name}</span
										>
									</HostHoverCard>
									{#if s.is_wildcard}
										<Badge
											variant="outline"
											class="px-1 text-[9px] font-normal text-muted-foreground"
										>
											wildcard
										</Badge>
									{/if}
									{#if !s.is_active}
										<Tooltip.Root>
											<Tooltip.Trigger>
												{#snippet child({ props })}
													<span {...props} class="text-[10px] text-muted-foreground/70">no DNS</span
													>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Content side="right">Did not resolve to an address</Tooltip.Content>
										</Tooltip.Root>
									{/if}
								</div>
								{#if s.cname}
									{@const prov = providerFor(s.cname)}
									<div
										class="mt-0.5 flex max-w-80 items-center gap-1 font-mono text-[10px] text-muted-foreground"
									>
										<CornerDownRight class="size-2.5 shrink-0" />
										{#if prov}
											{@const ProvIcon = PROVIDER_KIND_ICONS[prov.kind]}
											<Tooltip.Root>
												<Tooltip.Trigger>
													{#snippet child({ props })}
														<button
															{...props}
															type="button"
															class="inline-flex shrink-0 items-center gap-0.5 rounded-sm border border-border/70 px-1 font-sans text-[9px] hover:bg-accent hover:text-foreground"
															onclick={(e) => {
																stop(e);
																applyDsl(`cname:${prov.suffix}`);
															}}
														>
															<ProvIcon class="size-2.5" />
															{prov.label}
														</button>
													{/snippet}
												</Tooltip.Trigger>
												<Tooltip.Content>
													{PROVIDER_KIND_LABELS[prov.kind]} · filter hosts on {prov.label}
												</Tooltip.Content>
											</Tooltip.Root>
										{/if}
										<button
											type="button"
											class="truncate hover:text-foreground"
											onclick={(e) => {
												stop(e);
												applyDsl(`cname:${s.cname}`);
											}}
											title="Filter hosts pointing at {s.cname}"
										>
											{s.cname}
										</button>
									</div>
								{:else if redirected}
									<div
										class="mt-0.5 flex max-w-72 items-center gap-1 truncate font-mono text-[10px] text-muted-foreground"
									>
										<CornerDownRight class="size-2.5 shrink-0" />
										<span class="truncate">{s.final_url}</span>
									</div>
								{/if}
							</Table.Cell>

							{#each shownColumns as col (col.key)}
								{#if col.key === 'screenshot'}
									<Table.Cell>
										<ScreenshotThumb
											path={s.screenshot_path}
											alt={s.name}
											class="h-11 w-16"
											preview
										/>
									</Table.Cell>
								{:else if col.key === 'status'}
									<Table.Cell>
										<Tooltip.Root>
											<Tooltip.Trigger>
												{#snippet child({ props })}
													<span {...props} class="inline-flex items-center gap-1.5">
														<span
															class="size-1.5 rounded-full {STATUS_DOT[
																httpStatusClass(s.http_status)
															]}"
														></span>
														<span class="font-mono text-xs {httpStatusTextClass(s.http_status)}">
															{s.http_status ?? '—'}
														</span>
													</span>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Content>{httpStatusReason(s.http_status)}</Tooltip.Content>
										</Tooltip.Root>
									</Table.Cell>
								{:else if col.key === 'title'}
									<Table.Cell class="max-w-96 min-w-72">
										<div class="flex items-start gap-1.5">
											<span
												class="line-clamp-2 text-xs leading-4 whitespace-normal"
												title={s.page_title ?? undefined}
											>
												{s.page_title ?? '—'}
											</span>
											{#if s.page_title && (s.title_count ?? 0) > 1}
												{@const pageTitle = s.page_title}
												<SamePagePopover
													count={s.title_count ?? 0}
													title="{s.title_count} hosts show “{pageTitle}”"
													load={() => hostsWithTitle(pageTitle)}
													onHost={openHost}
													onFilter={() => applyDsl(exactToken('title', pageTitle))}
												/>
											{/if}
										</div>
									</Table.Cell>
								{:else if col.key === 'tech'}
									<Table.Cell class="min-w-52">
										{#if s.tech.length}
											<div class="flex flex-nowrap items-center gap-1 whitespace-nowrap">
												{#each s.tech.slice(0, MAX_TECH) as t (t)}
													<button
														type="button"
														onclick={(e) => {
															stop(e);
															applyDsl(`tech:${t}`);
														}}
													>
														<Badge
															variant="outline"
															class="cursor-pointer font-normal hover:bg-accent"
														>
															<TechIcon name={t} />
															{t}
														</Badge>
													</button>
												{/each}
												<OverflowPopover
													items={s.tech}
													shown={MAX_TECH}
													label="technologies"
													icons
													onSelect={(t) => applyDsl(`tech:${t}`)}
												/>
											</div>
										{:else}
											<span class="text-xs text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'ip'}
									<Table.Cell>
										<div class="flex items-center gap-1">
											{#if ips[0]}
												<button
													type="button"
													class="font-mono text-[11px] hover:underline"
													onclick={(e) => {
														stop(e);
														applyDsl(`ip:${ips[0]}`);
													}}
													title="Filter hosts on {ips[0]}"
												>
													{ips[0]}
												</button>
											{:else}
												<span class="text-xs text-muted-foreground">—</span>
											{/if}
											<OverflowPopover
												items={ips}
												shown={1}
												label="IP addresses"
												mono
												onSelect={(ip) => applyDsl(`ip:${ip}`)}
											/>
										</div>
										{#if s.is_cdn}
											<Tooltip.Root>
												<Tooltip.Trigger>
													{#snippet child({ props })}
														<span {...props} class="mt-0.5 inline-flex">
															<Badge variant="info" class="px-1 text-[9px] font-normal">
																{s.cdn_name ?? 'CDN'}
															</Badge>
														</span>
													{/snippet}
												</Tooltip.Trigger>
												<Tooltip.Content>Fronted by a CDN</Tooltip.Content>
											</Tooltip.Root>
										{/if}
									</Table.Cell>
								{:else if col.key === 'ports'}
									<Table.Cell>
										{#if ports.length}
											<div class="flex flex-nowrap items-center gap-0.5 whitespace-nowrap">
												{#each ports.slice(0, MAX_PORTS) as p (p)}
													<button
														type="button"
														onclick={(e) => {
															stop(e);
															applyDsl(`port:${p}`);
														}}
													>
														<Badge
															variant="outline"
															class="cursor-pointer px-1 font-mono text-[9px] font-normal hover:bg-accent {isSensitivePort(
																p
															)
																? 'text-warning'
																: ''}"
														>
															{p}
														</Badge>
													</button>
												{/each}
												<OverflowPopover
													items={ports.map(String)}
													shown={MAX_PORTS}
													label="open ports"
													mono
													onSelect={(p) => applyDsl(`port:${p}`)}
												/>
											</div>
										{:else}
											<span class="text-xs text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'cert'}
									<Table.Cell>
										{#if cert}
											<Tooltip.Root>
												<Tooltip.Trigger>
													{#snippet child({ props })}
														<span {...props}>
															{#if cert === 'expired'}
																<Badge variant="destructive" class="px-1 text-[10px] font-normal">
																	expired
																</Badge>
															{:else if cert === 'expiring'}
																<Badge variant="warning" class="px-1 text-[10px] font-normal">
																	{daysUntilExpiry(s)}d
																</Badge>
															{:else if cert === 'self-signed'}
																<Badge variant="warning" class="px-1 text-[10px] font-normal">
																	self-signed
																</Badge>
															{:else}
																<span class="text-[10px] text-muted-foreground">valid</span>
															{/if}
														</span>
													{/snippet}
												</Tooltip.Trigger>
												<Tooltip.Content>
													{s.tls_not_after
														? `Expires ${formatShortDate(s.tls_not_after)}`
														: 'Self-signed certificate'}
												</Tooltip.Content>
											</Tooltip.Root>
										{:else}
											<span class="text-[10px] text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'waf'}
									<Table.Cell>
										{#if s.waf}
											<Badge variant="secondary" class="px-1 text-[10px] font-normal">{s.waf}</Badge
											>
										{:else}
											<span class="text-[10px] text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'asn'}
									<Table.Cell class="max-w-44">
										{#if s.asn}
											<div class="truncate font-mono text-[11px]">AS{s.asn}</div>
											{#if s.asn_org}
												<div class="truncate text-[10px] text-muted-foreground" title={s.asn_org}>
													{s.asn_org}
												</div>
											{/if}
										{:else}
											<span class="text-[10px] text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'sources'}
									<Table.Cell>
										<div class="flex flex-nowrap items-center gap-0.5 whitespace-nowrap">
											{#each (s.sources ?? []).slice(0, MAX_SOURCES) as src (src)}
												<button
													type="button"
													onclick={(e) => {
														stop(e);
														applyDsl(`source:${src}`);
													}}
												>
													<Badge
														variant="outline"
														class="cursor-pointer px-1 text-[9px] font-normal text-muted-foreground hover:bg-accent"
													>
														{src}
													</Badge>
												</button>
											{/each}
											<OverflowPopover
												items={s.sources ?? []}
												shown={MAX_SOURCES}
												label="sources"
												onSelect={(src) => applyDsl(`source:${src}`)}
											/>
										</div>
									</Table.Cell>
								{:else if col.key === 'discovered'}
									<Table.Cell class="text-[11px] text-muted-foreground" title={s.discovered_at}>
										<div>{relativeTime(s.discovered_at)}</div>
										{#if s.discovered_at}
											<div class="text-[10px] text-muted-foreground/70">
												{formatShortDate(s.discovered_at)}
											</div>
										{/if}
									</Table.Cell>
								{:else if col.key === 'size'}
									<Table.Cell class="text-right font-mono text-[11px] text-muted-foreground">
										{formatBytes(s.content_length)}
									</Table.Cell>
								{:else if col.key === 'time'}
									<Table.Cell class="text-right font-mono text-[11px] text-muted-foreground">
										{formatResponseTime(s.response_time)}
									</Table.Cell>
								{/if}
							{/each}

							<Table.Cell class="pr-2">
								<div
									class="flex items-center justify-end gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
								>
									{#if s.http_url}
										<Button
											variant="ghost"
											size="icon-sm"
											class="size-6"
											href={s.http_url}
											target="_blank"
											rel="noreferrer noopener"
											onclick={stop}
											aria-label="Open {s.name} in browser"
										>
											<ExternalLink />
										</Button>
									{/if}
									<DropdownMenu.Root>
										<DropdownMenu.Trigger onclick={stop} onkeydown={stop}>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="icon-sm"
													class="size-6"
													aria-label="More actions for {s.name}"
												>
													<Ellipsis />
												</Button>
											{/snippet}
										</DropdownMenu.Trigger>
										<DropdownMenu.Content align="end" class="w-48" onclick={stop}>
											<DropdownMenu.Group>
												<DropdownMenu.Item onclick={() => copy(s.name)}>
													<Copy /> Copy host
												</DropdownMenu.Item>
												{#if s.http_url}
													<DropdownMenu.Item onclick={() => copy(s.http_url ?? '')}>
														<Link /> Copy URL
													</DropdownMenu.Item>
												{/if}
											</DropdownMenu.Group>
											{#if ips[0] || s.cname || s.favicon_hash}
												<DropdownMenu.Separator />
												<DropdownMenu.Group>
													<DropdownMenu.Label>Pivot</DropdownMenu.Label>
													{#if ips[0]}
														<DropdownMenu.Item onclick={() => applyDsl(`ip:${ips[0]}`)}>
															<Filter /> Same IP
														</DropdownMenu.Item>
													{/if}
													{#if s.cname}
														<DropdownMenu.Item onclick={() => applyDsl(`cname:${s.cname}`)}>
															<Filter /> Same CNAME
														</DropdownMenu.Item>
													{/if}
													{#if s.favicon_hash}
														<DropdownMenu.Item
															onclick={() => applyDsl(`favicon:${s.favicon_hash}`)}
														>
															<Filter /> Same favicon
														</DropdownMenu.Item>
													{/if}
												</DropdownMenu.Group>
											{/if}
										</DropdownMenu.Content>
									</DropdownMenu.Root>
								</div>
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>
	{/if}

	{#if !errored && total > 0}
		<ResultsPagination
			{total}
			page={pageIndex}
			{pageSize}
			onPage={(p) => (pageIndex = p)}
			onPageSize={(s) => {
				pageSize = s;
				pageIndex = 0;
			}}
		/>
	{/if}
</div>

<WebAssetDetailSheet
	sub={selected}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	{projectId}
	{scanId}
	index={selectedIndex}
	pageOffset={pageIndex * pageSize}
	{total}
	onStep={step}
	onFilter={applyDsl}
	onPivot={openHost}
/>

{#snippet sortHead(label: string, key: string)}
	<button
		type="button"
		class="-ml-1 inline-flex items-center gap-1 rounded px-1 hover:text-foreground"
		onclick={(e) => {
			e.stopPropagation();
			toggleSort(key);
		}}
	>
		{label}
		{#if sort.key === key}
			{#if sort.dir === 1}<ArrowUp class="size-3" />{:else}<ArrowDown class="size-3" />{/if}
		{:else}
			<ChevronsUpDown class="size-3 opacity-40" />
		{/if}
	</button>
{/snippet}
