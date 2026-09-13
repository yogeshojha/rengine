<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import FacetedFilter from '../faceted-filter.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import ViewControls from '../table/view-controls.svelte';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';
	import type { IpFacetSet, IpQuery } from '$lib/utilities/ip-groups';

	interface Props {
		query: IpQuery;
		facets: IpFacetSet;
		onQuery: (q: IpQuery) => void;
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
		{ value: 'sensitive', label: 'Sensitive' },
		{ value: 'hosted', label: 'Has hosts' },
		{ value: 'nocdn', label: 'No CDN' },
		{ value: 'v6', label: 'IPv6' }
	];

	let quick = $derived(
		[
			query.sensitiveOnly && 'sensitive',
			query.hostedOnly && 'hosted',
			query.cdn === 'no' && 'nocdn',
			query.version === 6 && 'v6'
		].filter((v): v is string => !!v)
	);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			sensitiveOnly: values.includes('sensitive'),
			hostedOnly: values.includes('hosted'),
			cdn: values.includes('nocdn') ? 'no' : query.cdn === 'no' ? 'any' : query.cdn,
			version: values.includes('v6') ? 6 : query.version === 6 ? 0 : query.version
		});
	}
	function setList<K extends 'asn' | 'country' | 'port' | 'service'>(key: K, value: string[]) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
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
		{#if facets.port.length}
			<FacetedFilter
				title="Port"
				options={facets.port}
				selected={query.port}
				onChange={(v) => setList('port', v)}
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
			dimension={SurfaceDimension.IPS}
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
