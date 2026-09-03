<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Filter from '@lucide/svelte/icons/filter';
	import Globe from '@lucide/svelte/icons/globe';
	import Network from '@lucide/svelte/icons/network';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';

	import * as Table from '$lib/components/ui/table';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';

	import SearchBar from './web-assets/search-bar.svelte';
	import OverflowPopover from './web-assets/overflow-popover.svelte';
	import TechIcon from './tech-icon.svelte';
	import ResultsPagination from './web-assets/results-pagination.svelte';
	import type { ColumnDef } from './web-assets/columns';
	import IpFilterBar from './ips/ip-filter-bar.svelte';
	import IpHoverCard from './ips/ip-hover-card.svelte';
	import IpDetailSheet from './ip-detail-sheet.svelte';

	import { ipsApi } from '$lib/api/scan-results';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { isSensitivePort } from '$lib/utilities/scan-correlation';
	import { appendToken, type IpGroupRead } from '$lib/utilities/scan-insights';
	import {
		compileIpQuery,
		emptyIpQuery,
		ipActiveFacetCount,
		EMPTY_IP_FACETS,
		IP_DSL_KEYS,
		type IpFacetSet,
		type IpQuery
	} from '$lib/utilities/ip-groups';
	import {
		RESULTS_PAGE_SIZE,
		SEARCH_DEBOUNCE_MS,
		RESULTS_SCROLL
	} from '$lib/utilities/scan-status';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
		onTab?: (tab: string, filter?: string) => void;
	}

	let { scanId, projectId, active = true, onTab }: Props = $props();

	interface Column extends ColumnDef {
		sort?: string;
		align?: 'right';
		width?: string;
	}
	const COLUMNS: Column[] = [
		{ key: 'asn', label: 'Network', sort: 'asn' },
		{ key: 'country', label: 'Country', sort: 'country', width: 'w-24' },
		{ key: 'ports', label: 'Ports', sort: 'ports' },
		{ key: 'hosts', label: 'Hosts', sort: 'hosts' },
		{ key: 'prefix', label: 'Prefix', width: 'w-36' },
		{ key: 'ptr', label: 'PTR' }
	];
	const DEFAULT_VISIBLE = ['asn', 'country', 'ports', 'hosts'];
	const DEFAULT_SORT = { key: 'hosts', dir: -1 as const };
	const MAX_PORTS = 4;
	const MAX_HOSTS = 2;

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
	const initialSort = initial.get('ip_sort')?.split(':') ?? [];
	let pendingIp = initial.get('ip');

	let query = $state<IpQuery>({ ...emptyIpQuery(), search: initial.get('ip_q') ?? '' });
	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.ipsColumns, null));
	let density = $state<string>(readPref(STORAGE_KEYS.ipsDensity, 'compact'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.ipsPageSize, RESULTS_PAGE_SIZE));
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('ip_page') ?? 1) - 1));

	let items = $state<IpGroupRead[]>([]);
	let total = $state(0);
	let loading = $state(true);
	let errored = $state(false);
	let facets = $state<IpFacetSet>(EMPTY_IP_FACETS);

	let selected = $state<IpGroupRead | null>(null);
	let drawerOpen = $state(false);
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;

	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let selectedIndex = $derived(selected ? items.findIndex((g) => g.ip === selected?.ip) : -1);
	let visible = $derived(
		visiblePref ??
			DEFAULT_VISIBLE.filter(
				(k) =>
					!(
						((k === 'asn' || k === 'country') && !facets.asn.length && !facets.country.length) ||
						(k === 'ports' && !facets.port.length)
					)
			)
	);
	let shownColumns = $derived(COLUMNS.filter((c) => visible.includes(c.key)));
	let filtered = $derived(ipActiveFacetCount(query) > 0 || !!query.search);
	let stripe = $derived(
		density === 'compact'
			? '[&_td]:h-12 [&_td]:py-2 [&_td]:align-top'
			: '[&_td]:h-16 [&_td]:py-3.5 [&_td]:align-top'
	);

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.ipsColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.ipsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.ipsPageSize, pageSize));

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let lastSig = '';

	async function runSearch() {
		const filter = compileIpQuery(query, sort.key, sort.dir, pageIndex * pageSize, pageSize);
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
			const res = await ipsApi.search(projectId, scanId, filter);
			if (my !== reqId) return;
			items = res.items;
			total = res.total;
			errored = false;
			if (pendingSelect) {
				selected = pendingSelect === 'first' ? (items[0] ?? null) : (items.at(-1) ?? null);
				pendingSelect = null;
			} else if (pendingIp) {
				const ip = pendingIp;
				pendingIp = null;
				const hit = items.find((g) => g.ip === ip);
				if (hit) open(hit);
				else openIp(ip);
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
		ipsApi
			.facets(pid, id)
			.then((f) => (facets = f))
			.catch(() => (facets = EMPTY_IP_FACETS));
	});

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams(location.search);
			const set = (k: string, v: string | null) => (v ? sp.set(k, v) : sp.delete(k));
			set('ip_q', query.search || null);
			set('ip_page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set(
				'ip_sort',
				sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir
					? `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`
					: null
			);
			set('ip', drawerOpen && selected ? selected.ip : null);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// URL state is best-effort
		}
	}
	$effect(() => {
		void query.search;
		void pageIndex;
		void sort.key;
		void sort.dir;
		void drawerOpen;
		void selected?.ip;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(g: IpGroupRead) {
		selected = g;
		drawerOpen = true;
	}
	async function openIp(ip: string) {
		const hit = items.find((g) => g.ip === ip);
		if (hit) return open(hit);
		try {
			const res = await ipsApi.search(
				projectId,
				scanId,
				compileIpQuery({ ...emptyIpQuery(), search: ip }, 'ip', 1, 0, 5)
			);
			const exact = res.items.find((g) => g.ip === ip);
			if (exact) open(exact);
			else toast.error('Address not found in this scan');
		} catch {
			toast.error('Could not load address');
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
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: IpQuery) {
		query = q;
		pageIndex = 0;
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function showHosts(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.('web-assets', filter);
	}
	async function copy(text: string) {
		if (await writeClipboard(text)) toast.success('Copied');
	}
	function scrollCursor() {
		document.querySelector(`[data-ip-row-index="${cursor}"]`)?.scrollIntoView({ block: 'nearest' });
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
		if (typing || drawerOpen || !items.length) return;
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
			keys={IP_DSL_KEYS}
			values={facets}
			placeholder="Search addresses, networks, hosts — or filter with port:22 is:sensitive asn:13335"
			onChange={(v) => setQuery({ ...query, search: v })}
		/>
	</div>

	<IpFilterBar
		{query}
		{facets}
		onQuery={setQuery}
		{total}
		columns={COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
	/>

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-2">
			{#each Array(8) as _, i (i)}
				<Skeleton class="h-12 w-full" />
			{/each}
		</div>
	{:else if errored}
		<EmptyState icon={TriangleAlert} title="Addresses could not be loaded">
			<Button size="sm" variant="outline" onclick={runSearch}>Retry</Button>
		</EmptyState>
	{:else if items.length === 0}
		{#if filtered}
			<EmptyState
				icon={SearchX}
				title="No addresses match"
				description="Widen the search or remove a filter."
			>
				<Button size="sm" variant="outline" onclick={() => setQuery(emptyIpQuery())}>
					Clear filters
				</Button>
			</EmptyState>
		{:else}
			<EmptyState
				icon={Network}
				title="No addresses yet"
				description="Addresses appear here once host names resolve or ports are found."
			/>
		{/if}
	{:else}
		<div class="overflow-hidden rounded-lg border transition-opacity {loading ? 'opacity-60' : ''}">
			<Table.Root containerClass={RESULTS_SCROLL}>
				<Table.Header class="sticky top-0 z-20 bg-background">
					<Table.Row class="hover:bg-transparent">
						<Table.Head class="sticky left-0 z-30 min-w-52 bg-background">
							{@render sortHead('Address', 'ip')}
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
					{#each items as g, i (g.ip)}
						{@const isSelected = drawerOpen && selected?.ip === g.ip}
						<Table.Row
							class="group cursor-pointer {cursor === i ? 'bg-muted/40' : ''}"
							data-state={isSelected ? 'selected' : undefined}
							data-ip-row-index={i}
							role="button"
							tabindex={0}
							onclick={() => open(g)}
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									open(g);
								}
							}}
						>
							<Table.Cell
								class="sticky left-0 z-10 bg-background group-hover:bg-[color-mix(in_oklab,var(--muted)_50%,var(--background))] group-data-[state=selected]:bg-muted"
							>
								<div class="flex items-center gap-1.5">
									<Tooltip.Root>
										<Tooltip.Trigger>
											{#snippet child({ props })}
												<span
													{...props}
													class="size-1.5 shrink-0 rounded-full {g.is_alive
														? 'bg-success'
														: 'bg-muted-foreground/40'}"
												></span>
											{/snippet}
										</Tooltip.Trigger>
										<Tooltip.Content side="right">
											{g.is_alive ? 'Responding' : 'No response observed'}
										</Tooltip.Content>
									</Tooltip.Root>
									<IpHoverCard group={g}>
										<span class="font-mono text-xs font-medium">{g.ip}</span>
									</IpHoverCard>
									{#if g.version === 6}
										<Badge
											variant="outline"
											class="px-1 text-[9px] font-normal text-muted-foreground"
										>
											v6
										</Badge>
									{/if}
									{#if g.is_cdn}
										<Badge variant="info" class="px-1 text-[9px] font-normal">
											<TechIcon name={g.cdn_name ?? ''} class="size-2.5" />
											{g.cdn_name ?? 'CDN'}
										</Badge>
									{/if}
									{#if g.has_sensitive}
										<Tooltip.Root>
											<Tooltip.Trigger>
												{#snippet child({ props })}
													<span {...props}>
														<TriangleAlert class="size-3 text-warning" />
													</span>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Content>Exposes a sensitive service</Tooltip.Content>
										</Tooltip.Root>
									{/if}
								</div>
							</Table.Cell>

							{#each shownColumns as col (col.key)}
								{#if col.key === 'asn'}
									<Table.Cell class="max-w-56">
										{#if g.asn}
											<button
												type="button"
												class="block max-w-full text-left hover:underline"
												onclick={(e) => {
													stop(e);
													applyDsl(`asn:${g.asn}`);
												}}
												title="Filter addresses in AS{g.asn}"
											>
												<span class="block font-mono text-[11px]">AS{g.asn}</span>
												{#if g.asn_org}
													<span class="block truncate text-[10px] text-muted-foreground">
														{g.asn_org}
													</span>
												{/if}
											</button>
										{:else}
											<span class="text-[10px] text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'country'}
									<Table.Cell class="text-xs text-muted-foreground">
										{#if g.country}
											<button
												type="button"
												class="hover:text-foreground hover:underline"
												onclick={(e) => {
													stop(e);
													applyDsl(`country:${g.country}`);
												}}
											>
												{g.country}
											</button>
										{:else}
											—
										{/if}
									</Table.Cell>
								{:else if col.key === 'ports'}
									<Table.Cell>
										{#if g.ports.length}
											<div class="flex flex-nowrap items-center gap-0.5 whitespace-nowrap">
												{#each g.ports.slice(0, MAX_PORTS) as p (p.id)}
													<button
														type="button"
														onclick={(e) => {
															stop(e);
															applyDsl(`port:${p.number}`);
														}}
													>
														<Badge
															variant="outline"
															class="cursor-pointer px-1 font-mono text-[9px] font-normal hover:bg-accent {isSensitivePort(
																p.number
															)
																? 'text-warning'
																: ''}"
														>
															{p.number}
														</Badge>
													</button>
												{/each}
												<OverflowPopover
													items={g.ports.map((p) =>
														p.service_name ? `${p.number}/${p.service_name}` : String(p.number)
													)}
													shown={MAX_PORTS}
													label="open ports"
													mono
													onSelect={(v) => applyDsl(`port:${v.split('/')[0]}`)}
												/>
											</div>
										{:else}
											<span class="text-[10px] text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'hosts'}
									<Table.Cell class="min-w-64">
										{#if g.host_count}
											<div class="flex flex-nowrap items-center gap-1 whitespace-nowrap">
												<span class="w-6 text-right font-mono text-xs tabular-nums">
													{g.host_count}
												</span>
												{#each g.hosts.slice(0, MAX_HOSTS) as h (h)}
													<button
														type="button"
														onclick={(e) => {
															stop(e);
															showHosts(`name:${h}`);
														}}
														title="Open {h} in Web Assets"
													>
														<Badge
															variant="outline"
															class="max-w-40 cursor-pointer font-mono text-[9px] font-normal hover:bg-accent"
														>
															<span class="truncate">{h}</span>
														</Badge>
													</button>
												{/each}
												<OverflowPopover
													items={g.hosts}
													shown={MAX_HOSTS}
													label="hosts"
													mono
													onSelect={(h) => showHosts(`name:${h}`)}
												/>
											</div>
										{:else}
											<span class="text-[10px] text-muted-foreground">—</span>
										{/if}
									</Table.Cell>
								{:else if col.key === 'prefix'}
									<Table.Cell class="font-mono text-[11px] text-muted-foreground">
										{g.prefix ?? '—'}
									</Table.Cell>
								{:else if col.key === 'ptr'}
									<Table.Cell class="max-w-56 truncate font-mono text-[11px] text-muted-foreground">
										{g.ptr_hostnames.join(', ') || '—'}
									</Table.Cell>
								{/if}
							{/each}

							<Table.Cell class="pr-2">
								<div
									class="flex items-center justify-end gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
								>
									{#if g.host_count}
										<Tooltip.Root>
											<Tooltip.Trigger>
												{#snippet child({ props })}
													<Button
														{...props}
														variant="ghost"
														size="icon-sm"
														class="size-6"
														onclick={(e) => {
															stop(e);
															showHosts(`ip:${g.ip}`);
														}}
														aria-label="Show hosts on {g.ip} in Web Assets"
													>
														<Globe />
													</Button>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Content>Hosts in Web Assets</Tooltip.Content>
										</Tooltip.Root>
									{/if}
									<DropdownMenu.Root>
										<DropdownMenu.Trigger onclick={stop} onkeydown={stop}>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="icon-sm"
													class="size-6"
													aria-label="More actions for {g.ip}"
												>
													<Ellipsis />
												</Button>
											{/snippet}
										</DropdownMenu.Trigger>
										<DropdownMenu.Content align="end" class="w-48" onclick={stop}>
											<DropdownMenu.Group>
												<DropdownMenu.Item onclick={() => copy(g.ip)}>
													<Copy /> Copy address
												</DropdownMenu.Item>
												{#if g.host_count}
													<DropdownMenu.Item onclick={() => showHosts(`ip:${g.ip}`)}>
														<Globe /> Hosts in Web Assets
													</DropdownMenu.Item>
												{/if}
											</DropdownMenu.Group>
											{#if g.asn || g.country}
												<DropdownMenu.Separator />
												<DropdownMenu.Group>
													<DropdownMenu.Label>Pivot</DropdownMenu.Label>
													{#if g.asn}
														<DropdownMenu.Item onclick={() => applyDsl(`asn:${g.asn}`)}>
															<Filter /> Same network
														</DropdownMenu.Item>
													{/if}
													{#if g.country}
														<DropdownMenu.Item onclick={() => applyDsl(`country:${g.country}`)}>
															<Filter /> Same country
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

<IpDetailSheet
	group={selected}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={pageIndex * pageSize}
	{total}
	onStep={step}
	onFilter={applyDsl}
	onHosts={showHosts}
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
