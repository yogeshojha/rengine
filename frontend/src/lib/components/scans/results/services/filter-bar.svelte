<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import FacetedFilter from '../faceted-filter.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import ViewControls from '../table/view-controls.svelte';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';
	import type { ServiceFacetSet, ServiceQuery } from '$lib/utilities/services';

	interface Props {
		query: ServiceQuery;
		facets: ServiceFacetSet;
		onQuery: (q: ServiceQuery) => void;
		dimensions: QueryGroupSpec[];
		columns: TableColumn[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
		sorts: SortOption[];
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
		query,
		facets,
		onQuery,
		dimensions,
		columns,
		visible,
		onToggleColumn,
		density,
		onDensity,
		sorts,
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

	const QUICK = [
		{ value: 'new', label: 'New' },
		{ value: 'sensitive', label: 'Sensitive' },
		{ value: 'nonweb', label: 'Non-web' },
		{ value: 'named', label: 'Identified' },
		{ value: 'nocdn', label: 'No CDN' }
	];

	let quick = $derived(
		[
			query.newOnly && 'new',
			query.sensitiveOnly && 'sensitive',
			query.http === 'no' && 'nonweb',
			query.namedOnly && 'named',
			query.cdn === 'no' && 'nocdn'
		].filter((v): v is string => !!v)
	);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			newOnly: values.includes('new'),
			sensitiveOnly: values.includes('sensitive'),
			namedOnly: values.includes('named'),
			http: values.includes('nonweb') ? 'no' : query.http === 'no' ? 'any' : query.http,
			cdn: values.includes('nocdn') ? 'no' : query.cdn === 'no' ? 'any' : query.cdn
		});
	}
	function setList<K extends 'port' | 'service' | 'source' | 'asn' | 'country'>(
		key: K,
		value: string[]
	) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
		{#if facets.service.length}
			<FacetedFilter
				title="Service"
				options={facets.service}
				selected={query.service}
				onChange={(v) => setList('service', v)}
			/>
		{/if}
		{#if facets.port.length}
			<FacetedFilter
				title="Port"
				options={facets.port}
				selected={query.port}
				onChange={(v) => setList('port', v)}
			/>
		{/if}
		{#if facets.source.length > 1}
			<FacetedFilter
				title="Evidence"
				options={facets.source}
				selected={query.source}
				onChange={(v) => setList('source', v)}
			/>
		{/if}
		{#if facets.asn.length}
			<FacetedFilter
				title="Network"
				options={facets.asn}
				selected={query.asn}
				onChange={(v) => setList('asn', v)}
			/>
		{/if}
		{#if facets.country.length}
			<FacetedFilter
				title="Country"
				options={facets.country}
				selected={query.country}
				onChange={(v) => setList('country', v)}
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
		<ViewControls
			dimension={SurfaceDimension.SERVICES}
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
		/>
	</div>
</div>
