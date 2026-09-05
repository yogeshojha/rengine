<script lang="ts">
	import { untrack } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';

	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Outline from '../endpoints/outline.svelte';
	import EndpointDetailSheet from '../endpoint-detail-sheet.svelte';
	import CompositionBar from '../overview/composition-bar.svelte';
	import type { Segment } from '../overview/composition-bar.svelte';
	import { ENDPOINT_COLUMNS, DEFAULT_VISIBLE_OUTLINE_COLUMNS } from '../endpoints/columns';
	import { endpointsApi } from '$lib/api/scan-results';
	import { endpointQuerySchema } from '$lib/stores/query-schema.svelte';
	import {
		ENDPOINT_CLASS_FILL,
		ENDPOINT_CLASS_LABELS,
		ENDPOINT_CLASS_ORDER,
		EndpointClass
	} from '$lib/config/endpoints';
	import { appendToken, exactToken } from '$lib/utilities/scan-insights';
	import {
		highlightTerms,
		type EndpointFilter,
		type EndpointRead,
		type EndpointSummary,
		type EndpointTree
	} from '$lib/utilities/endpoints';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

	interface Props {
		host: string;
		projectId: string;
		scanId: string;
		compact?: boolean;
		onOpenEndpoints?: (host: string) => void;
		onSummary?: (summary: EndpointSummary | null) => void;
	}

	let { host, projectId, scanId, compact = false, onOpenEndpoints, onSummary }: Props = $props();

	let search = $state('');
	let hideStatic = $state(true);
	let tree = $state<EndpointTree | null>(null);
	let loading = $state(true);
	let summary = $state<EndpointSummary | null>(null);
	let selected = $state<EndpointRead | null>(null);
	let drawerOpen = $state(false);
	let sort = $state<{ key: string; dir: 1 | -1 }>({ key: 'relevance', dir: -1 });
	let req = 0;

	const columns = ENDPOINT_COLUMNS.filter((c) => DEFAULT_VISIBLE_OUTLINE_COLUMNS.includes(c.key));

	$effect(() => {
		void endpointQuerySchema.load();
	});

	let known = $derived((name: string) => endpointQuerySchema.byName.has(name));
	let terms = $derived(highlightTerms(search, known));
	let filter = $derived<EndpointFilter>({
		q: search.trim() || null,
		host,
		dir_path: null,
		subtree: true,
		endpoint_class: null,
		source: null,
		interest: null,
		status_class: null,
		probed: null,
		new: false,
		hide_static: hideStatic,
		sort: sort.key,
		direction: sort.dir === 1 ? 'asc' : 'desc',
		page: 1,
		size: 1
	});
	let sig = $derived(JSON.stringify(filter));

	async function load() {
		const my = ++req;
		loading = true;
		try {
			const res = await endpointsApi.tree(projectId, scanId, 'host', filter);
			if (my === req) tree = res;
		} catch {
			if (my === req) tree = null;
		} finally {
			if (my === req) loading = false;
		}
	}

	$effect(() => {
		void sig;
		const handle = setTimeout(() => untrack(load), search ? SEARCH_DEBOUNCE_MS : 0);
		return () => clearTimeout(handle);
	});

	$effect(() => {
		void host;
		void scanId;
		untrack(() => {
			search = '';
			summary = null;
			endpointsApi
				.summary(projectId, scanId, host)
				.then((s) => {
					summary = s;
					onSummary?.(s);
				})
				.catch(() => {
					summary = null;
					onSummary?.(null);
				});
		});
	});

	let segments = $derived.by<Segment[]>(() =>
		ENDPOINT_CLASS_ORDER.filter((k) => (summary?.by_class[k] ?? 0) > 0).map((k) => ({
			key: k,
			label: ENDPOINT_CLASS_LABELS[k],
			count: summary?.by_class[k] ?? 0,
			color: ENDPOINT_CLASS_FILL[k] ?? ENDPOINT_CLASS_FILL[EndpointClass.OTHER],
			filter: `class:${k}`
		}))
	);

	function applyToken(token: string) {
		search = appendToken(search, token);
	}
	function pivotHost(name: string) {
		search = appendToken(search, exactToken('host', name));
	}
	function toggleSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: 1 };
	}
	function open(e: EndpointRead) {
		selected = e;
		drawerOpen = true;
	}
</script>

<div class="flex flex-col">
	{#if !compact && summary && summary.total > 0}
		<div class="flex flex-col gap-3 border-b px-5 py-4">
			<CompositionBar
				{segments}
				total={summary.total}
				label="endpoints by kind"
				onSelect={applyToken}
			/>
		</div>
	{/if}

	<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
		<div class="relative min-w-0 flex-1 basis-56">
			<Search
				class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={search}
				placeholder="Find a path on this host"
				class="h-9 pl-8 font-mono text-xs"
				aria-label="Find a path on this host"
			/>
		</div>
		<ToggleGroup.Root
			type="multiple"
			value={hideStatic ? ['static'] : []}
			onValueChange={(v) => (hideStatic = v.includes('static'))}
			variant="outline"
			aria-label="Static files"
		>
			<ToggleGroup.Item value="static" class="h-9 px-3 text-sm font-normal">
				Hide static
			</ToggleGroup.Item>
		</ToggleGroup.Root>
		{#if onOpenEndpoints}
			<Button variant="outline" size="sm" class="h-9 gap-1.5" onclick={() => onOpenEndpoints(host)}>
				Open in Endpoints <ArrowUpRight class="size-3.5" />
			</Button>
		{/if}
	</div>

	{#if tree && tree.nodes.length === 0 && !loading}
		<EmptyState
			icon={Waypoints}
			title={search || hideStatic ? 'No paths match' : 'No paths on this host'}
			description={search
				? 'Widen the search.'
				: hideStatic
					? 'Every discovered path on this host is a static file.'
					: 'URL discovery found nothing on this host.'}
			class="rounded-none border-0 bg-transparent py-12"
		>
			{#if hideStatic && !search}
				<Button size="sm" variant="outline" onclick={() => (hideStatic = false)}>
					Show static files
				</Button>
			{/if}
		</EmptyState>
	{:else}
		<Outline
			{projectId}
			{scanId}
			{tree}
			{loading}
			{filter}
			{terms}
			{columns}
			pad="py-2"
			embedded
			searching={!!search.trim()}
			paused={drawerOpen}
			selectedId={drawerOpen ? (selected?.id ?? null) : null}
			sortKey={sort.key}
			sortDir={sort.dir}
			onSort={toggleSort}
			onOpen={open}
			onFilter={applyToken}
			onHost={pivotHost}
		/>
	{/if}
</div>

<EndpointDetailSheet
	endpoint={selected}
	{projectId}
	{scanId}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={-1}
	pageOffset={0}
	total={0}
	onStep={() => {}}
	onFilter={applyToken}
/>
