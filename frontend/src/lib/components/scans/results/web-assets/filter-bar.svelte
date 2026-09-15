<script lang="ts">
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import Layers from '@lucide/svelte/icons/layers';
	import Image from '@lucide/svelte/icons/image';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Toggle } from '$lib/components/ui/toggle';
	import FacetedFilter from '../faceted-filter.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import ViewControls from '../table/view-controls.svelte';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { SubdomainFacetSet, WebAssetQuery } from '$lib/utilities/scan-insights';
	import { querySchema } from '$lib/stores/query-schema.svelte';

	interface Props {
		sorts: SortOption[];
		query: WebAssetQuery;
		facets: SubdomainFacetSet;
		onQuery: (q: WebAssetQuery) => void;
		view: string;
		onView: (v: string) => void;
		columns: TableColumn[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
		onlyShots: boolean;
		groupRenders: boolean;
		onGroupRenders: (v: boolean) => void;
		onOnlyShots: (v: boolean) => void;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		refreshing: boolean;
		onRefresh: () => void;
		projectId?: string;
		scanId?: string;
		exportFilters?: Record<string, unknown>;
		groupBy: string;
		onGroupBy: (key: string) => void;
	}

	let {
		sorts,
		query,
		facets,
		onQuery,
		view,
		onView,
		columns,
		visible,
		onToggleColumn,
		density,
		onDensity,
		onlyShots,
		groupRenders,
		onGroupRenders,
		onOnlyShots,
		sortKey,
		sortDir,
		onSort,
		refreshing,
		onRefresh,
		groupBy,
		onGroupBy,
		projectId = '',
		scanId = '',
		exportFilters = {}
	}: Props = $props();

	let dimensions = $derived(querySchema.schema.group_dimensions);

	const QUICK = [
		{ value: 'new', label: 'New' },
		{ value: 'issues', label: 'Issues' },
		{ value: 'nowaf', label: 'No WAF' }
	];

	let quick = $derived(
		[query.newOnly && 'new', query.issuesOnly && 'issues', query.waf === 'none' && 'nowaf'].filter(
			(v): v is string => !!v
		)
	);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			newOnly: values.includes('new'),
			issuesOnly: values.includes('issues'),
			waf: values.includes('nowaf') ? 'none' : query.waf === 'none' ? 'any' : query.waf
		});
	}
	function setList<K extends 'tech' | 'service' | 'cert' | 'hygiene' | 'posture' | 'source'>(
		key: K,
		value: string[]
	) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
		{#if facets.tech.length}
			<FacetedFilter
				title="Tech"
				options={facets.tech}
				selected={query.tech}
				onChange={(v) => setList('tech', v)}
			/>
		{/if}
		{#if facets.service.length}
			<FacetedFilter
				title="Service"
				options={facets.service}
				selected={query.service}
				onChange={(v) => setList('service', v)}
			/>
		{/if}
		{#if facets.cert.length}
			<FacetedFilter
				title="Cert"
				options={facets.cert}
				selected={query.cert}
				onChange={(v) => setList('cert', v)}
			/>
		{/if}
		{#if facets.hygiene.length}
			<FacetedFilter
				title="Hygiene"
				options={facets.hygiene}
				selected={query.hygiene}
				onChange={(v) => setList('hygiene', v)}
			/>
		{/if}
		{#if facets.posture.length}
			<FacetedFilter
				title="Posture"
				options={facets.posture}
				selected={query.posture}
				onChange={(v) => setList('posture', v)}
			/>
		{/if}
		{#if facets.source.length}
			<FacetedFilter
				title="Source"
				options={facets.source}
				selected={query.source}
				onChange={(v) => setList('source', v)}
			/>
		{/if}
		<ToggleGroup.Root
			type="multiple"
			value={quick}
			onValueChange={setQuick}
			variant="outline"
			aria-label="Filters"
		>
			{#each QUICK as q (q.value)}
				<ToggleGroup.Item value={q.value} class="h-9 px-3 text-sm font-normal">
					{q.label}
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
	</div>

	<div class="flex items-center gap-2">
		<ToggleGroup.Root
			type="single"
			variant="outline"
			value={view}
			onValueChange={(v) => v && onView(v)}
			aria-label="View"
		>
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<ToggleGroup.Item {...props} value="table" aria-label="List view" class="h-9 px-3">
							<Rows3 class="h-4 w-4" />
						</ToggleGroup.Item>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content>List view</Tooltip.Content>
			</Tooltip.Root>
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<ToggleGroup.Item {...props} value="gallery" aria-label="Gallery view" class="h-9 px-3">
							<LayoutGrid class="h-4 w-4" />
						</ToggleGroup.Item>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content>Gallery view</Tooltip.Content>
			</Tooltip.Root>
		</ToggleGroup.Root>

		{#if view === 'gallery'}
			<Toggle
				pressed={onlyShots}
				onPressedChange={onOnlyShots}
				variant="outline"
				class="h-9 gap-2 px-3 text-sm font-normal"
				aria-label="Only hosts with a screenshot"
			>
				<Image class="h-4 w-4" />
				<span class="hidden sm:inline">With screenshot</span>
			</Toggle>
			<Toggle
				pressed={groupRenders}
				onPressedChange={onGroupRenders}
				variant="outline"
				class="h-9 gap-2 px-3 text-sm font-normal"
				aria-label="Group web assets that render the same page"
			>
				<Layers class="h-4 w-4" />
				<span class="hidden sm:inline">Group identical</span>
			</Toggle>
		{/if}

		<ViewControls
			dimension={SurfaceDimension.WEB_ASSETS}
			{dimensions}
			{groupBy}
			{onGroupBy}
			{sorts}
			{sortKey}
			{sortDir}
			{onSort}
			{columns}
			{visible}
			{onToggleColumn}
			{density}
			{onDensity}
			{refreshing}
			{onRefresh}
			{projectId}
			{scanId}
			{exportFilters}
			showColumns={view === 'table'}
		/>
	</div>
</div>
