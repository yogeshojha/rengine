<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Search from '@lucide/svelte/icons/search';
	import Layers from '@lucide/svelte/icons/layers';
	import * as Card from '$lib/components/ui/card';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Item from '$lib/components/ui/item';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import HorizontalBarChart from '../charts/horizontal-bar-chart.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { cn } from '$lib/utils';
	import type { Facet, InsightTally } from '$lib/utilities/scan-insights';

	interface Props {
		top: InsightTally[];
		total: number;
		hosts: number;
		scanId: string;
		projectId: string;
		class?: string;
		onFilter: (search: string) => void;
	}

	let { top, total, hosts, scanId, projectId, class: className, onFilter }: Props = $props();

	const TOP_CHART = 10;
	const LIST_LIMIT = 200;

	let open = $state(false);
	let query = $state('');
	let items = $state<Facet[]>([]);
	let loading = $state(false);
	let errored = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;
	let seq = 0;

	function fetchList(q: string) {
		const my = ++seq;
		loading = true;
		errored = false;
		subdomainsApi
			.tech(projectId, scanId, q, LIST_LIMIT)
			.then((r) => {
				if (my !== seq) return;
				items = r;
			})
			.catch(() => {
				if (my === seq) errored = true;
			})
			.finally(() => {
				if (my === seq) loading = false;
			});
	}

	$effect(() => {
		if (!open) return;
		const q = query;
		clearTimeout(timer);
		timer = setTimeout(() => fetchList(q), q ? SEARCH_DEBOUNCE_MS : 0);
		return () => clearTimeout(timer);
	});

	function pick(name: string) {
		open = false;
		onFilter(`tech:${name}`);
	}

	let max = $derived(items[0]?.count ?? 1);
	let chartBars = $derived(top.slice(0, TOP_CHART).map((t) => ({ label: t.name, count: t.count })));
</script>

<Card.Root class={cn('flex flex-col gap-4 py-5', className)}>
	<Card.Header class="gap-1">
		<Card.Title>Technology stack</Card.Title>
		<Card.Description>Detected across {hosts.toLocaleString()} live hosts</Card.Description>
	</Card.Header>
	<Card.Content class="flex-1">
		<div class="flex flex-wrap gap-1.5">
			{#each top as t (t.name)}
				<button type="button" class="cursor-pointer" onclick={() => onFilter(`tech:${t.name}`)}>
					<Badge variant="secondary" class="gap-1.5 font-normal hover:bg-secondary/70">
						{t.name}
						<span class="text-muted-foreground tabular-nums">{t.count.toLocaleString()}</span>
					</Badge>
				</button>
			{/each}
		</div>
	</Card.Content>
	<Card.Footer class="text-sm">
		<Button variant="link" size="sm" class="h-auto gap-1 px-0" onclick={() => (open = true)}>
			View all {total.toLocaleString()} technologies <ChevronRight class="size-3.5" />
		</Button>
	</Card.Footer>
</Card.Root>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		<Sheet.Header class="border-b border-border px-6 py-5">
			<Sheet.Title class="flex items-center gap-2">
				<Layers class="size-4 text-muted-foreground" />
				Technology stack
			</Sheet.Title>
			<Sheet.Description>
				{total.toLocaleString()} technologies across {hosts.toLocaleString()} live hosts. Select one to
				list its hosts.
			</Sheet.Description>
		</Sheet.Header>
		<div class="border-b border-border px-6 py-4">
			<InputGroup.Root>
				<InputGroup.Addon><Search class="size-4" /></InputGroup.Addon>
				<InputGroup.Input
					placeholder="Search technologies"
					bind:value={query}
					aria-label="Search technologies"
				/>
			</InputGroup.Root>
		</div>
		<ScrollArea class="min-h-0 flex-1">
			{#if !query && chartBars.length}
				<div class="border-b border-border px-6 py-5">
					<p class="mb-3 text-sm font-medium">Most common</p>
					<HorizontalBarChart
						bars={chartBars}
						valueLabel="Hosts"
						labelWidth={132}
						onSelect={pick}
					/>
				</div>
			{/if}
			<div class="px-3 py-3">
				{#if loading && !items.length}
					<div class="flex flex-col gap-2 px-3">
						{#each Array(6) as _, i (i)}
							<Skeleton class="h-9 w-full" />
						{/each}
					</div>
				{:else if errored}
					<EmptyState compact title="Technologies could not be loaded">
						<Button variant="outline" size="sm" onclick={() => fetchList(query)}>Retry</Button>
					</EmptyState>
				{:else if !items.length}
					<EmptyState
						compact
						title="No technologies match"
						description="Try a shorter search term."
					/>
				{:else}
					<Item.Group class="gap-0.5">
						{#each items as t (t.value)}
							<Item.Root size="sm" class="hover:bg-muted/60">
								{#snippet child({ props })}
									<button type="button" {...props} onclick={() => pick(t.value)}>
										<Item.Content class="gap-1.5">
											<Item.Title class="font-normal">{t.label}</Item.Title>
											<div class="h-1 w-full overflow-hidden rounded-full bg-muted">
												<div
													class="h-full rounded-full bg-chart-1"
													style="width:{Math.max(2, (t.count / max) * 100)}%"
												></div>
											</div>
										</Item.Content>
										<Item.Actions class="text-sm tabular-nums">
											<span class="font-medium">{t.count.toLocaleString()}</span>
											<ChevronRight class="size-4 text-muted-foreground/60" />
										</Item.Actions>
									</button>
								{/snippet}
							</Item.Root>
						{/each}
					</Item.Group>
					{#if items.length >= LIST_LIMIT}
						<p class="px-3 pt-3 text-xs text-muted-foreground">
							Showing the first {LIST_LIMIT}. Refine the search to see more.
						</p>
					{/if}
				{/if}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>
