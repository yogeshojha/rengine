<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Layers from '@lucide/svelte/icons/layers';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RankedList from './ranked-list.svelte';
	import type { RankedRow } from './ranked-list.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import type { Facet } from '$lib/utilities/scan-insights';

	interface Props {
		open: boolean;
		total: number;
		hosts: number;
		scanId: string;
		projectId: string;
		onPick: (name: string) => void;
	}

	let { open = $bindable(false), total, hosts, scanId, projectId, onPick }: Props = $props();

	const LIST_LIMIT = 200;

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
				if (my === seq) items = r;
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

	let rows = $derived<RankedRow[]>(
		items.map((t) => ({ key: t.value, label: t.label, count: t.count, filter: t.value }))
	);

	function pick(name: string) {
		open = false;
		onPick(name);
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		<Sheet.Header class="border-b px-6 py-5">
			<Sheet.Title class="flex items-center gap-2">
				<Layers class="size-4 text-muted-foreground" />
				Technology stack
			</Sheet.Title>
			<Sheet.Description>
				{total.toLocaleString()} technologies across {hosts.toLocaleString()} web hosts. Select one to
				list its hosts.
			</Sheet.Description>
		</Sheet.Header>
		<div class="border-b px-6 py-4">
			<InputGroup.Root>
				<InputGroup.Addon><Search class="size-4" /></InputGroup.Addon>
				<InputGroup.Input
					placeholder="Search technologies…"
					bind:value={query}
					aria-label="Search technologies"
				/>
			</InputGroup.Root>
		</div>
		<ScrollArea class="min-h-0 flex-1">
			<div class="px-6 py-3">
				{#if loading && !items.length}
					<div class="flex flex-col gap-2">
						{#each Array(8) as _, i (i)}
							<Skeleton class="h-10 w-full" />
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
					<RankedList {rows} base={hosts} onSelect={pick}>
						{#snippet icon(r)}
							<TechIcon name={r.label} class="size-4" />
						{/snippet}
					</RankedList>
					{#if items.length >= LIST_LIMIT}
						<p class="pt-3 text-xs text-muted-foreground">
							Showing the first {LIST_LIMIT}. Refine the search to see more.
						</p>
					{/if}
				{/if}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>
