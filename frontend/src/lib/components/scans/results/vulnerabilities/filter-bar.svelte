<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import FacetedFilter from '../faceted-filter.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import ViewControls from '../table/view-controls.svelte';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';
	import type { Facet } from '$lib/utilities/scan-insights';
	import type { VulnFacetSet, VulnQuery } from '$lib/utilities/vulns';

	interface Props {
		query: VulnQuery;
		facets: VulnFacetSet;
		onQuery: (q: VulnQuery) => void;
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
		columnsLocked?: boolean;
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
		columnsLocked = false,
		projectId = '',
		scanId = '',
		exportFilters = {}
	}: Props = $props();

	const QUICK = [
		{ value: 'new', label: 'New' },
		{ value: 'kev', label: 'Known exploited' },
		{ value: 'cve', label: 'Has a CVE' },
		{ value: 'corroborated', label: 'Confirmed' },
		{ value: 'noinfo', label: 'Hide info' },
		{ value: 'reviewed', label: 'Show reviewed' }
	];

	let quick = $derived(
		[
			query.newOnly && 'new',
			query.kevOnly && 'kev',
			query.cveOnly && 'cve',
			query.corroboratedOnly && 'corroborated',
			!query.includeInfo && 'noinfo',
			query.includeSuppressed && 'reviewed'
		].filter((v): v is string => !!v)
	);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			newOnly: values.includes('new'),
			kevOnly: values.includes('kev'),
			cveOnly: values.includes('cve'),
			corroboratedOnly: values.includes('corroborated'),
			includeInfo: !values.includes('noinfo'),
			includeSuppressed: values.includes('reviewed')
		});
	}

	function options(list: VulnFacetSet[keyof VulnFacetSet]): Facet[] {
		return list.map((f) => ({ value: f.name, label: f.label ?? f.name, count: f.count }));
	}

	function setList<K extends 'templates' | 'tags' | 'hosts' | 'protocols' | 'states' | 'scanners'>(
		key: K,
		value: string[]
	) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
		{#if facets.template.length}
			<FacetedFilter
				title="Check"
				options={options(facets.template)}
				selected={query.templates}
				onChange={(v) => setList('templates', v)}
			/>
		{/if}
		{#if facets.tag.length}
			<FacetedFilter
				title="Category"
				options={options(facets.tag)}
				selected={query.tags}
				onChange={(v) => setList('tags', v)}
			/>
		{/if}
		{#if facets.host.length}
			<FacetedFilter
				title="Host"
				options={options(facets.host)}
				selected={query.hosts}
				onChange={(v) => setList('hosts', v)}
			/>
		{/if}
		{#if facets.protocol.length > 1}
			<FacetedFilter
				title="Type"
				options={options(facets.protocol)}
				selected={query.protocols}
				onChange={(v) => setList('protocols', v)}
			/>
		{/if}
		{#if facets.scanner.length > 1}
			<FacetedFilter
				title="Scanner"
				options={options(facets.scanner)}
				selected={query.scanners}
				onChange={(v) => setList('scanners', v)}
			/>
		{/if}
		{#if facets.state.length > 1}
			<FacetedFilter
				title="Review"
				options={options(facets.state)}
				selected={query.states}
				onChange={(v) => setList('states', v)}
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
			dimension={SurfaceDimension.VULNERABILITIES}
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
			{columnsLocked}
		/>
	</div>
</div>
