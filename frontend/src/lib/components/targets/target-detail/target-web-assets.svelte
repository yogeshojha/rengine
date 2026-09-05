<script lang="ts">
	import { untrack } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Globe from '@lucide/svelte/icons/globe';
	import X from '@lucide/svelte/icons/x';
	import * as Card from '$lib/components/ui/card';
	import * as Empty from '$lib/components/ui/empty';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Toggle } from '$lib/components/ui/toggle';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ListHeader from '$lib/components/scans/results/table/list-header.svelte';
	import SortMenu from '$lib/components/scans/results/table/sort-menu.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import AssetRow from './web-assets/asset-row.svelte';
	import { ASSET_COLUMNS, ASSET_LEAD_COLUMNS, DEFAULT_ASSET_COLUMNS } from './web-assets/columns';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { AssetSort, AssetState, TargetAssetPage } from '$lib/types/target-asset';
	import { ASSET_SORTS } from '$lib/types/target-asset';

	interface Props {
		targetId: string;
		onScan: () => void;
	}

	let { targetId, onScan }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const PAGE_SIZE = 50;

	let page = $state<TargetAssetPage | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let search = $state('');
	let debounced = $state('');
	let assetState = $state<AssetState>('all');
	let live = $state(false);
	let sort = $state<AssetSort>('name');
	let order = $state<'asc' | 'desc'>('asc');
	let pageIndex = $state(0);
	let debounce: ReturnType<typeof setTimeout> | undefined;

	let columns = $derived(ASSET_COLUMNS.filter((c) => DEFAULT_ASSET_COLUMNS.includes(c.key)));
	let facets = $derived(page?.facets ?? null);
	let rows = $derived(page?.items ?? []);
	let tabs = $derived.by(() => {
		const out = [{ key: 'all', label: 'All' }];
		if (facets && facets.total > 0 && !facets.baseline) {
			out.push({ key: 'current', label: 'Current' });
			if (facets.new > 0) out.push({ key: 'new', label: 'New' });
			if (facets.gone > 0) out.push({ key: 'gone', label: 'Gone' });
		}
		return out;
	});
	let counts = $derived(
		facets
			? { all: facets.total, current: facets.current, new: facets.new, gone: facets.gone }
			: null
	);
	let filtered = $derived(debounced.trim() !== '' || assetState !== 'all' || live);

	$effect(() => {
		const value = search;
		clearTimeout(debounce);
		debounce = setTimeout(() => {
			debounced = value;
			pageIndex = 0;
		}, SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(debounce);
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const query = { targetId, project, debounced, assetState, live, sort, order, pageIndex };
		if (!project || !targetId) return;
		untrack(() => load(query.project!.id));
	});

	async function load(projectId: string) {
		loading = true;
		try {
			page = await targetsApi.searchAssets(targetId, projectId, {
				search: debounced.trim() || null,
				state: assetState,
				live,
				sort,
				order,
				limit: PAGE_SIZE,
				offset: pageIndex * PAGE_SIZE
			});
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load web assets';
		} finally {
			loading = false;
		}
	}

	function setSort(key: string) {
		if (sort === key) order = order === 'asc' ? 'desc' : 'asc';
		else {
			sort = key as AssetSort;
			order = key === 'name' ? 'asc' : 'desc';
		}
		pageIndex = 0;
	}

	function reset() {
		search = '';
		debounced = '';
		assetState = 'all';
		live = false;
		pageIndex = 0;
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="border-b px-2">
		<CountTabs
			{tabs}
			value={assetState}
			{counts}
			onChange={(key) => {
				assetState = key as AssetState;
				pageIndex = 0;
			}}
		/>
	</div>

	<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
		<div class="relative min-w-0 flex-1">
			<Search
				class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={search}
				placeholder="Search host, title or address"
				class="h-9 pl-9"
				aria-label="Search web assets"
			/>
		</div>
		<Hint text="Only assets that answered an HTTP request">
			{#snippet child(props)}
				<span {...props} class="inline-flex">
					<Toggle
						variant="outline"
						size="sm"
						pressed={live}
						onPressedChange={(v) => {
							live = v;
							pageIndex = 0;
						}}
						class="h-9"
					>
						Responding
						{#if facets}
							<span class="ml-1.5 text-xs text-muted-foreground tabular-nums">
								{facets.live.toLocaleString()}
							</span>
						{/if}
					</Toggle>
				</span>
			{/snippet}
		</Hint>
		<SortMenu
			sorts={[...ASSET_SORTS]}
			sortKey={sort}
			sortDir={order === 'asc' ? 1 : -1}
			onSort={setSort}
		/>
		<Button
			variant="outline"
			size="icon"
			class="size-9"
			aria-label="Refresh"
			onclick={() => projectsStore.activeProject && load(projectsStore.activeProject.id)}
		>
			<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
		</Button>
	</div>

	{#if loading && !page}
		<div class="divide-y">
			{#each Array(8) as _, i (i)}
				<div class="flex items-center gap-3 px-4 py-3">
					<Skeleton class="h-5 flex-1" />
					<Skeleton class="hidden h-5 w-32 sm:block" />
					<Skeleton class="hidden h-5 w-24 sm:block" />
				</div>
			{/each}
		</div>
	{:else if error}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Media class="size-12 rounded-2xl bg-destructive/10">
					<TriangleAlert class="size-6 text-destructive" />
				</Empty.Media>
				<Empty.Title>Web assets could not be loaded</Empty.Title>
				<Empty.Description class="max-w-md">{error}</Empty.Description>
			</Empty.Header>
		</Empty.Root>
	{:else if rows.length === 0 && filtered}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Title>No web assets match this filter</Empty.Title>
				<Empty.Description>Widen the search or clear the filters.</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" class="gap-2" onclick={reset}>
					<X class="size-4" /> Clear filters
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if rows.length === 0}
		<Empty.Root class="py-16">
			<Empty.Header>
				<Empty.Media
					variant="icon"
					class="size-14 rounded-2xl bg-muted text-muted-foreground/60 [&_svg:not([class*='size-'])]:size-6"
				>
					<Globe />
				</Empty.Media>
				<Empty.Title>No web assets yet</Empty.Title>
				<Empty.Description class="max-w-sm">
					Run a scan that discovers hosts to build this inventory.
				</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button class="gap-2" onclick={onScan}>Start scan</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<ListHeader
			lead={ASSET_LEAD_COLUMNS}
			{columns}
			sortKey={sort}
			sortDir={order === 'asc' ? 1 : -1}
			onSort={setSort}
		/>
		<div class="divide-y">
			{#each rows as asset (asset.name)}
				<AssetRow {asset} {columns} term={debounced.trim()} />
			{/each}
		</div>
		<ResultsPagination
			total={page?.total ?? 0}
			page={pageIndex}
			pageSize={PAGE_SIZE}
			noun={WEB.noun}
			plural={WEB.nounPlural}
			onPage={(p) => (pageIndex = p)}
		/>
	{/if}
</Card.Root>
