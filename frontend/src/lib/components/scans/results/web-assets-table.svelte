<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Star from '@lucide/svelte/icons/star';
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ChevronsUpDown from '@lucide/svelte/icons/chevrons-up-down';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ImageOff from '@lucide/svelte/icons/image-off';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

	import * as Table from '$lib/components/ui/table';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as Empty from '$lib/components/ui/empty';

	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechBadges from './tech-badges.svelte';
	import FacetedFilter from './faceted-filter.svelte';
	import WebAssetDetailSheet from './web-asset-detail-sheet.svelte';

	import { subdomainsApi } from '$lib/api/subdomains';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusTextClass,
		isSensitivePort
	} from '$lib/utilities/scan-correlation';
	import {
		certState,
		daysUntilExpiry,
		activeFacetCount,
		emptyQuery,
		compileQuery,
		type WebAssetQuery,
		type SubdomainFacetSet
	} from '$lib/utilities/scan-insights';
	import {
		RESULTS_PAGE_SIZE as PAGE_SIZE,
		SEARCH_DEBOUNCE_MS,
		RESULTS_SCROLL
	} from '$lib/utilities/scan-status';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
		query?: WebAssetQuery;
	}

	let { scanId, projectId, active = true, query = $bindable(emptyQuery()) }: Props = $props();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	const TOGGLE_COLS = [
		{ key: 'screenshot', label: 'Screenshot' },
		{ key: 'status', label: 'Status' },
		{ key: 'title', label: 'Title' },
		{ key: 'tech', label: 'Tech' },
		{ key: 'ip', label: 'IP / CDN' },
		{ key: 'ports', label: 'Ports' },
		{ key: 'waf', label: 'WAF' },
		{ key: 'cert', label: 'Cert' },
		{ key: 'asn', label: 'Network' },
		{ key: 'sources', label: 'Sources' },
		{ key: 'size', label: 'Size' },
		{ key: 'time', label: 'Time' }
	];
	const EMPTY_FACETS: SubdomainFacetSet = {
		status: [],
		tech: [],
		service: [],
		source: [],
		cert: []
	};

	let visible = $state<string[]>([
		'screenshot',
		'status',
		'title',
		'tech',
		'ip',
		'ports',
		'size',
		'time'
	]);
	let view = $state('table');
	let density = $state('compact');
	let sort = $state<{ key: string; dir: 1 | -1 }>({ key: 'name', dir: 1 });
	let page = $state(0);

	let items = $state<SubdomainRead[]>([]);
	let total = $state(0);
	let loading = $state(true);
	let errored = $state(false);
	let facets = $state<SubdomainFacetSet>(EMPTY_FACETS);

	let selected = $state<SubdomainRead | null>(null);
	let drawerOpen = $state(false);

	let scanTotal = $derived(facets.status.reduce((n, f) => n + f.count, 0));
	let pageCount = $derived(Math.max(1, Math.ceil(total / PAGE_SIZE)));
	let selectedIndex = $derived(selected ? items.findIndex((s) => s.name === selected?.name) : -1);

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let lastSig = '';

	async function runSearch() {
		const filter = compileQuery(query, sort.key, sort.dir, page * PAGE_SIZE, PAGE_SIZE);
		const sig = JSON.stringify({ ...filter, offset: 0 });
		if (sig !== lastSig && page !== 0) {
			lastSig = sig;
			page = 0;
			return;
		}
		lastSig = sig;
		const my = ++reqId;
		loading = true;
		try {
			const res = await subdomainsApi.search(projectId, scanId, filter);
			if (my === reqId) {
				items = res.items;
				total = res.total;
				errored = false;
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
		void page;
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

	function open(s: SubdomainRead) {
		selected = s;
		drawerOpen = true;
	}
	function step(dir: -1 | 1) {
		const next = selectedIndex + dir;
		if (next >= 0 && next < items.length) selected = items[next];
	}
	function toggleSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: 1 };
		page = 0;
	}
	function toggleCol(key: string) {
		visible = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setFacet<K extends keyof WebAssetQuery>(key: K, value: WebAssetQuery[K]) {
		query = { ...query, [key]: value };
		page = 0;
	}
	function statusLabel(code: number | null): string {
		return code == null ? '—' : String(code);
	}
</script>

<div class="flex flex-col gap-3">
	<div class="mx-auto flex w-full max-w-2xl items-center gap-2">
		<div class="relative flex-1">
			<Search
				class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				value={query.search}
				oninput={(e) => setFacet('search', e.currentTarget.value)}
				placeholder="Search or filter — try  status:200 tech:nginx waf:none  ·  is:live"
				class="h-10 pl-9 font-mono text-sm"
			/>
			{#if query.search}
				<Button
					variant="ghost"
					size="icon"
					class="absolute top-1/2 right-1 size-7 -translate-y-1/2"
					onclick={() => setFacet('search', '')}
					aria-label="Clear search"
				>
					<X class="size-3.5" />
				</Button>
			{/if}
		</div>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<FacetedFilter
			title="Status"
			options={facets.status}
			selected={query.status}
			onChange={(v) => setFacet('status', v)}
		/>
		<FacetedFilter
			title="Tech"
			options={facets.tech}
			selected={query.tech}
			onChange={(v) => setFacet('tech', v)}
		/>
		<FacetedFilter
			title="Service"
			options={facets.service}
			selected={query.service}
			onChange={(v) => setFacet('service', v)}
		/>
		{#if facets.cert.length}
			<FacetedFilter
				title="Cert"
				options={facets.cert}
				selected={query.cert}
				onChange={(v) => setFacet('cert', v)}
			/>
		{/if}
		<FacetedFilter
			title="Source"
			options={facets.source}
			selected={query.source}
			onChange={(v) => setFacet('source', v)}
		/>

		<Separator orientation="vertical" class="mx-0.5 h-5" />
		<Button
			variant={query.liveOnly ? 'secondary' : 'outline'}
			size="sm"
			class="h-8"
			onclick={() => setFacet('liveOnly', !query.liveOnly)}>Live</Button
		>
		<Button
			variant={query.hasScreenshot ? 'secondary' : 'outline'}
			size="sm"
			class="h-8"
			onclick={() => setFacet('hasScreenshot', !query.hasScreenshot)}>Screenshot</Button
		>
		<Button
			variant={query.waf === 'none' ? 'secondary' : 'outline'}
			size="sm"
			class="h-8"
			onclick={() => setFacet('waf', query.waf === 'none' ? 'any' : 'none')}>No WAF</Button
		>
		<Button
			variant={query.issuesOnly ? 'secondary' : 'outline'}
			size="sm"
			class="h-8"
			onclick={() => setFacet('issuesOnly', !query.issuesOnly)}>Issues</Button
		>

		{#if activeFacetCount(query) > 0 || query.search}
			<Button
				variant="ghost"
				size="sm"
				class="h-8 text-muted-foreground"
				onclick={() => (query = emptyQuery())}
			>
				Reset <X data-icon="inline-end" />
			</Button>
		{/if}

		<div class="ml-auto flex items-center gap-2">
			<span class="text-xs tabular-nums text-muted-foreground">
				{total.toLocaleString()}{scanTotal ? ` of ${scanTotal.toLocaleString()}` : ''}
			</span>
			<ToggleGroup.Root type="single" bind:value={view} variant="outline" size="sm">
				<ToggleGroup.Item value="table" class="text-xs">Table</ToggleGroup.Item>
				<ToggleGroup.Item value="gallery" class="text-xs">Gallery</ToggleGroup.Item>
			</ToggleGroup.Root>
			{#if view === 'table'}
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button variant="outline" size="sm" class="h-8" {...props}>
								<Columns3 data-icon="inline-start" /> Columns
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-40">
						<DropdownMenu.Label>Toggle columns</DropdownMenu.Label>
						<DropdownMenu.Separator />
						{#each TOGGLE_COLS as col (col.key)}
							<DropdownMenu.CheckboxItem
								checked={visible.includes(col.key)}
								onCheckedChange={() => toggleCol(col.key)}
							>
								{col.label}
							</DropdownMenu.CheckboxItem>
						{/each}
					</DropdownMenu.Content>
				</DropdownMenu.Root>
				<ToggleGroup.Root type="single" bind:value={density} variant="outline" size="sm">
					<ToggleGroup.Item value="compact" class="text-xs">Compact</ToggleGroup.Item>
					<ToggleGroup.Item value="cozy" class="text-xs">Cozy</ToggleGroup.Item>
				</ToggleGroup.Root>
			{/if}
		</div>
	</div>

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-2">
			{#each Array(8) as _, i (i)}
				<Skeleton class="h-9 w-full" />
			{/each}
		</div>
	{:else if errored}
		<Empty.Root class="rounded-lg border border-dashed py-16">
			<Empty.Header>
				<Empty.Media variant="icon"><TriangleAlert /></Empty.Media>
				<Empty.Title class="text-sm">Couldn't load web assets</Empty.Title>
				<Empty.Description>The request failed. Retry or adjust the filters.</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" onclick={runSearch}>Retry</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if items.length === 0}
		<Empty.Root class="rounded-lg border border-dashed py-16">
			<Empty.Header>
				{#if activeFacetCount(query) === 0 && !query.search}
					<Empty.Title class="text-sm">No web assets discovered yet</Empty.Title>
					<Empty.Description>Nothing has been probed for this scan so far.</Empty.Description>
				{:else}
					<Empty.Title class="text-sm">No matching hosts</Empty.Title>
					<Empty.Description>Adjust the search or filters to widen results.</Empty.Description>
				{/if}
			</Empty.Header>
		</Empty.Root>
	{:else if view === 'gallery'}
		<ScrollArea class={RESULTS_SCROLL}>
			<div
				class="grid grid-cols-2 gap-3 transition-opacity sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 {loading
					? 'opacity-60'
					: ''}"
			>
				{#each items as s (s.id)}
					<button
						type="button"
						class="group flex flex-col overflow-hidden rounded-lg border text-left transition-colors hover:border-foreground/30"
						onclick={() => open(s)}
					>
						{#if s.screenshot_path}
							<ScreenshotThumb
								path={s.screenshot_path}
								alt={s.name}
								class="aspect-video w-full"
								interactive={false}
							/>
						{:else}
							<div
								class="flex aspect-video w-full items-center justify-center bg-muted/40 text-muted-foreground"
							>
								<ImageOff class="size-6" />
							</div>
						{/if}
						<div class="flex flex-col gap-1 p-2">
							<div class="flex items-center gap-1.5">
								<Badge
									variant="outline"
									class="font-mono text-[10px] {httpStatusTextClass(s.http_status)}"
								>
									{statusLabel(s.http_status)}
								</Badge>
								<span class="truncate font-mono text-xs">{s.name}</span>
							</div>
							{#if s.page_title}<span class="truncate text-[11px] text-muted-foreground"
									>{s.page_title}</span
								>{/if}
						</div>
					</button>
				{/each}
			</div>
		</ScrollArea>
	{:else}
		<div class="overflow-hidden rounded-lg border transition-opacity {loading ? 'opacity-60' : ''}">
			<Table.Root containerClass={RESULTS_SCROLL}>
				<Table.Header class="sticky top-0 z-20 bg-background">
					<Table.Row class="hover:bg-transparent">
						<Table.Head class="sticky left-0 z-30 bg-background">
							{@render sortHead('Host', 'name')}
						</Table.Head>
						{#if visible.includes('screenshot')}<Table.Head class="w-16">Shot</Table.Head>{/if}
						{#if visible.includes('status')}<Table.Head class="w-20"
								>{@render sortHead('Status', 'status')}</Table.Head
							>{/if}
						{#if visible.includes('title')}<Table.Head>Title</Table.Head>{/if}
						{#if visible.includes('tech')}<Table.Head>Tech</Table.Head>{/if}
						{#if visible.includes('ip')}<Table.Head>IP / CDN</Table.Head>{/if}
						{#if visible.includes('ports')}<Table.Head>Ports</Table.Head>{/if}
						{#if visible.includes('waf')}<Table.Head>WAF</Table.Head>{/if}
						{#if visible.includes('cert')}<Table.Head>Cert</Table.Head>{/if}
						{#if visible.includes('asn')}<Table.Head>Network</Table.Head>{/if}
						{#if visible.includes('sources')}<Table.Head>Sources</Table.Head>{/if}
						{#if visible.includes('size')}<Table.Head class="text-right"
								>{@render sortHead('Size', 'size')}</Table.Head
							>{/if}
						{#if visible.includes('time')}<Table.Head class="text-right"
								>{@render sortHead('Time', 'time')}</Table.Head
							>{/if}
						<Table.Head class="w-10"></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body class={density === 'compact' ? '[&_td]:py-1.5' : '[&_td]:py-3'}>
					{#each items as s (s.id)}
						{@const cert = certState(s)}
						{@const sps = s.ports ?? []}
						<Table.Row
							class="cursor-pointer"
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
							<Table.Cell class="sticky left-0 z-10 bg-background">
								<div class="flex items-center gap-1.5">
									{#if s.is_important}<Star
											class="size-3 shrink-0 fill-warning text-warning"
										/>{/if}
									<span class="font-mono text-xs font-medium">{s.name}</span>
									{#if s.is_wildcard}<Badge
											variant="outline"
											class="px-1 text-[9px] font-normal text-muted-foreground">wildcard</Badge
										>{/if}
									{#if !s.is_active}<Badge
											variant="outline"
											class="px-1 text-[9px] font-normal text-muted-foreground">inactive</Badge
										>{/if}
								</div>
								{#if s.cname}<div class="truncate pl-4 font-mono text-[10px] text-muted-foreground">
										→ {s.cname}
									</div>{/if}
							</Table.Cell>
							{#if visible.includes('screenshot')}
								<Table.Cell>
									<ScreenshotThumb
										path={s.screenshot_path}
										alt={s.name}
										class="h-9 w-14"
										interactive={false}
									/>
								</Table.Cell>
							{/if}
							{#if visible.includes('status')}
								<Table.Cell>
									<span class="font-mono text-xs {httpStatusTextClass(s.http_status)}"
										>{statusLabel(s.http_status)}</span
									>
								</Table.Cell>
							{/if}
							{#if visible.includes('title')}
								<Table.Cell class="max-w-56">
									<div class="truncate text-xs">{s.page_title ?? '—'}</div>
									{#if s.webserver}<div class="truncate text-[10px] text-muted-foreground">
											{s.webserver}
										</div>{/if}
								</Table.Cell>
							{/if}
							{#if visible.includes('tech')}<Table.Cell
									><TechBadges tech={s.tech} max={3} /></Table.Cell
								>{/if}
							{#if visible.includes('ip')}
								<Table.Cell>
									<div class="flex items-center gap-1">
										<span class="font-mono text-[11px]">{s.resolved_ips?.[0] ?? '—'}</span>
										{#if (s.resolved_ips?.length ?? 0) > 1}<span
												class="text-[10px] text-muted-foreground">+{s.resolved_ips.length - 1}</span
											>{/if}
										{#if s.is_cdn}<Badge variant="info" class="px-1 text-[9px] font-normal"
												>{s.cdn_name ?? 'CDN'}</Badge
											>{/if}
									</div>
								</Table.Cell>
							{/if}
							{#if visible.includes('ports')}
								<Table.Cell>
									<div class="flex flex-wrap gap-0.5">
										{#each sps.slice(0, 4) as p (p)}
											<Badge
												variant="outline"
												class="px-1 font-mono text-[9px] font-normal {isSensitivePort(p)
													? 'text-warning'
													: ''}">{p}</Badge
											>
										{/each}
										{#if sps.length > 4}<span class="text-[10px] text-muted-foreground"
												>+{sps.length - 4}</span
											>{/if}
									</div>
								</Table.Cell>
							{/if}
							{#if visible.includes('waf')}
								<Table.Cell>
									{#if s.waf}<Badge variant="secondary" class="px-1 text-[10px] font-normal"
											>{s.waf}</Badge
										>{:else}<span class="text-[10px] text-muted-foreground">—</span>{/if}
								</Table.Cell>
							{/if}
							{#if visible.includes('cert')}
								<Table.Cell>
									{#if cert === 'expired'}<Badge
											variant="destructive"
											class="px-1 text-[10px] font-normal">expired</Badge
										>
									{:else if cert === 'expiring'}<Badge
											variant="warning"
											class="px-1 text-[10px] font-normal">{daysUntilExpiry(s)}d</Badge
										>
									{:else if cert === 'self-signed'}<Badge
											variant="warning"
											class="px-1 text-[10px] font-normal">self-signed</Badge
										>
									{:else if cert === 'valid'}<span class="text-[10px] text-muted-foreground"
											>valid</span
										>
									{:else}<span class="text-[10px] text-muted-foreground">—</span>{/if}
								</Table.Cell>
							{/if}
							{#if visible.includes('asn')}
								<Table.Cell class="max-w-40">
									{#if s.asn}<div class="truncate text-[11px]">
											<span class="font-mono">AS{s.asn}</span>
											{s.asn_org ?? ''}
										</div>{:else}<span class="text-[10px] text-muted-foreground">—</span>{/if}
								</Table.Cell>
							{/if}
							{#if visible.includes('sources')}
								<Table.Cell>
									<div class="flex flex-wrap gap-0.5">
										{#each (s.sources ?? []).slice(0, 2) as src (src)}
											<Badge
												variant="outline"
												class="px-1 text-[9px] font-normal text-muted-foreground">{src}</Badge
											>
										{/each}
										{#if (s.sources?.length ?? 0) > 2}<span
												class="text-[10px] text-muted-foreground">+{s.sources.length - 2}</span
											>{/if}
									</div>
								</Table.Cell>
							{/if}
							{#if visible.includes('size')}<Table.Cell
									class="text-right font-mono text-[11px] text-muted-foreground"
									>{formatBytes(s.content_length)}</Table.Cell
								>{/if}
							{#if visible.includes('time')}<Table.Cell
									class="text-right font-mono text-[11px] text-muted-foreground"
									>{formatResponseTime(s.response_time)}</Table.Cell
								>{/if}
							<Table.Cell>
								{#if s.http_url}
									<a
										href={s.http_url}
										target="_blank"
										rel="noreferrer noopener"
										onclick={(e) => e.stopPropagation()}
										class="text-muted-foreground hover:text-foreground"
										aria-label="Open in browser"
									>
										<ExternalLink class="size-3.5" />
									</a>
								{/if}
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>
	{/if}

	{#if total > PAGE_SIZE}
		<div class="flex items-center justify-between text-xs text-muted-foreground">
			<span class="tabular-nums">
				{(page * PAGE_SIZE + 1).toLocaleString()}–{Math.min(
					(page + 1) * PAGE_SIZE,
					total
				).toLocaleString()}
				of {total.toLocaleString()}
			</span>
			<div class="flex items-center gap-2">
				<Button
					variant="outline"
					size="sm"
					class="h-7"
					disabled={page === 0 || loading}
					onclick={() => (page = page - 1)}
				>
					<ChevronLeft data-icon="inline-start" /> Prev
				</Button>
				<span class="tabular-nums">Page {page + 1} / {pageCount.toLocaleString()}</span>
				<Button
					variant="outline"
					size="sm"
					class="h-7"
					disabled={page >= pageCount - 1 || loading}
					onclick={() => (page = page + 1)}
				>
					Next <ChevronRight data-icon="inline-end" />
				</Button>
			</div>
		</div>
	{/if}
</div>

<WebAssetDetailSheet
	sub={selected}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	{projectId}
	{scanId}
	index={selectedIndex}
	total={items.length}
	onStep={step}
	onHost={(name) => {
		query = { ...emptyQuery(), search: `name:${name}` };
		drawerOpen = false;
	}}
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
