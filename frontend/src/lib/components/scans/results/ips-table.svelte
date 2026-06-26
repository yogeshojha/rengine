<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import Server from '@lucide/svelte/icons/server';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Table from '$lib/components/ui/table';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty';
	import { ipsApi } from '$lib/api/scan-results';
	import { isSensitivePort } from '$lib/utilities/scan-correlation';
	import type { IpGroupRead } from '$lib/utilities/scan-insights';
	import {
		RESULTS_PAGE_SIZE as PAGE_SIZE,
		SEARCH_DEBOUNCE_MS,
		RESULTS_SCROLL
	} from '$lib/utilities/scan-status';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
	}

	let { scanId, projectId, active = true }: Props = $props();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let search = $state('');
	let page = $state(0);
	let items = $state<IpGroupRead[]>([]);
	let total = $state(0);
	let loading = $state(true);
	let errored = $state(false);
	let selected = $state<IpGroupRead | null>(null);
	let open = $state(false);

	let pageCount = $derived(Math.max(1, Math.ceil(total / PAGE_SIZE)));

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let lastSearch = '';

	async function load() {
		if (search !== lastSearch && page !== 0) {
			lastSearch = search;
			page = 0;
			return;
		}
		lastSearch = search;
		const my = ++reqId;
		loading = true;
		try {
			const res = await ipsApi.groups(projectId, scanId, {
				search: search || undefined,
				limit: PAGE_SIZE,
				offset: page * PAGE_SIZE
			});
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
		void search;
		void page;
		void scanId;
		void projectId;
		if (!seen) return;
		if (timer) clearTimeout(timer);
		timer = setTimeout(load, SEARCH_DEBOUNCE_MS);
		return () => {
			if (timer) clearTimeout(timer);
		};
	});

	function openGroup(g: IpGroupRead) {
		selected = g;
		open = true;
	}
</script>

<div class="flex flex-col gap-3">
	<div class="relative max-w-sm">
		<Search
			class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
		/>
		<Input bind:value={search} placeholder="Filter IPs, networks, PTR…" class="h-9 pl-9" />
	</div>

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-2">
			{#each Array(6) as _, i (i)}
				<Skeleton class="h-9 w-full" />
			{/each}
		</div>
	{:else if errored}
		<Empty.Root class="rounded-lg border border-dashed py-16">
			<Empty.Header>
				<Empty.Media variant="icon"><TriangleAlert /></Empty.Media>
				<Empty.Title class="text-sm">Couldn't load IP infrastructure</Empty.Title>
				<Empty.Description>The request failed.</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" onclick={load}>Retry</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if items.length === 0}
		<Empty.Root class="rounded-lg border border-dashed py-16">
			<Empty.Header>
				{#if search.trim()}
					<Empty.Title class="text-sm">No matching IPs</Empty.Title>
					<Empty.Description>Nothing matches the current filter.</Empty.Description>
				{:else}
					<Empty.Title class="text-sm">No IP infrastructure yet</Empty.Title>
					<Empty.Description>No hosts have been resolved for this scan so far.</Empty.Description>
				{/if}
			</Empty.Header>
		</Empty.Root>
	{:else}
		<div class="rounded-lg border transition-opacity {loading ? 'opacity-60' : ''}">
			<Table.Root containerClass={RESULTS_SCROLL}>
				<Table.Header class="sticky top-0 z-20 bg-background">
					<Table.Row class="hover:bg-transparent">
						<Table.Head>IP</Table.Head>
						<Table.Head>Network</Table.Head>
						<Table.Head>Country</Table.Head>
						<Table.Head>Ports</Table.Head>
						<Table.Head class="text-right">Hosts</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body class="[&_td]:py-2">
					{#each items as g (g.ip)}
						<Table.Row
							class="cursor-pointer"
							role="button"
							tabindex={0}
							onclick={() => openGroup(g)}
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									openGroup(g);
								}
							}}
						>
							<Table.Cell>
								<div class="flex items-center gap-1.5">
									<span
										class="size-1.5 rounded-full {g.is_alive
											? 'bg-success'
											: 'bg-muted-foreground/40'}"
									></span>
									<span class="font-mono text-xs">{g.ip}</span>
									{#if g.is_cdn}<Badge variant="info" class="px-1 text-[9px] font-normal"
											>{g.cdn_name ?? 'CDN'}</Badge
										>{/if}
								</div>
							</Table.Cell>
							<Table.Cell class="max-w-56">
								{#if g.asn}<div class="truncate text-xs">
										<span class="font-mono">AS{g.asn}</span>
										{g.asn_org ?? ''}
									</div>{:else}<span class="text-[11px] text-muted-foreground">—</span>{/if}
							</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{g.country ?? '—'}</Table.Cell>
							<Table.Cell>
								<div class="flex flex-wrap gap-0.5">
									{#each g.ports.slice(0, 6) as p (p.id)}
										<Badge
											variant="outline"
											class="px-1 font-mono text-[9px] font-normal {isSensitivePort(p.number)
												? 'text-warning'
												: ''}">{p.number}</Badge
										>
									{/each}
									{#if g.ports.length > 6}<span class="text-[10px] text-muted-foreground"
											>+{g.ports.length - 6}</span
										>{/if}
								</div>
							</Table.Cell>
							<Table.Cell class="text-right font-mono text-xs tabular-nums"
								>{g.host_count}</Table.Cell
							>
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

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		{#if selected}
			<Sheet.Header class="gap-1 border-b border-border p-4">
				<div class="flex items-center gap-2">
					<Network class="size-4 text-muted-foreground" />
					<Sheet.Title class="font-mono text-sm">{selected.ip}</Sheet.Title>
					{#if selected.is_cdn}<Badge variant="info" class="font-normal"
							>{selected.cdn_name ?? 'CDN'}</Badge
						>{/if}
				</div>
				{#if selected.asn}
					<p class="text-xs text-muted-foreground">
						AS{selected.asn} · {selected.asn_org ?? '—'}{selected.country
							? ` · ${selected.country}`
							: ''}
					</p>
				{/if}
			</Sheet.Header>
			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-5 p-4">
					{#if selected.prefix || selected.ptr_hostnames.length}
						<div class="divide-y divide-border/60">
							{#if selected.prefix}
								<div class="flex justify-between gap-4 py-1 text-xs">
									<span class="text-muted-foreground">Prefix</span>
									<span class="font-mono">{selected.prefix}</span>
								</div>
							{/if}
							{#if selected.ptr_hostnames.length}
								<div class="flex justify-between gap-4 py-1 text-xs">
									<span class="text-muted-foreground">PTR</span>
									<span class="break-all text-right font-mono"
										>{selected.ptr_hostnames.join(', ')}</span
									>
								</div>
							{/if}
						</div>
					{/if}

					{#if selected.ports.length}
						<div class="flex flex-col gap-1.5">
							<div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
								<Plug class="size-3.5" /> <span class="uppercase">Open ports</span>
							</div>
							<div class="flex flex-wrap gap-1">
								{#each selected.ports as p (p.id)}
									<Badge
										variant="outline"
										class="font-mono text-[11px] font-normal {isSensitivePort(p.number)
											? 'text-warning'
											: ''}"
									>
										{p.number}{p.service_name ? `/${p.service_name}` : ''}
									</Badge>
								{/each}
							</div>
						</div>
					{/if}

					<div class="flex flex-col gap-1.5">
						<div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
							<Server class="size-3.5" />
							<span class="uppercase">Hosts on this IP ({selected.host_count})</span>
						</div>
						<div class="flex flex-wrap gap-1">
							{#each selected.hosts as h (h)}
								<Badge variant="secondary" class="font-mono text-[10px] font-normal">{h}</Badge>
							{/each}
							{#if selected.host_count > selected.hosts.length}
								<span class="text-xs text-muted-foreground"
									>+{selected.host_count - selected.hosts.length} more</span
								>
							{/if}
						</div>
					</div>
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
