<script lang="ts">
	import { appendToken, tokenize } from '$lib/utilities/scan-insights';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import FacetedFilter from '../faceted-filter.svelte';
	import { EVIDENCE_LABELS, Evidence } from '$lib/config/evidence';
	import { SurfaceDimension } from '$lib/config/surface';
	import ViewControls from '../table/view-controls.svelte';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';
	import type { Facet } from '$lib/utilities/scan-insights';
	import type { VulnFacetSet, VulnQuery } from '$lib/utilities/vulns';

	interface Props {
		query: VulnQuery;
		facets: VulnFacetSet;
		/** until the facets load, the pickers hold their place disabled */
		facetsLoaded?: boolean;
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
		onShortcuts?: () => void;
	}

	let {
		query,
		facets,
		facetsLoaded = true,
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
		exportFilters = {},
		onShortcuts
	}: Props = $props();

	const NEW_TOKEN = 'is:new';

	const QUICK = [
		{ value: 'new', label: 'New' },
		{ value: 'kev', label: 'Known exploited' },
		{ value: 'cve', label: 'Has a CVE' },
		{ value: 'corroborated', label: EVIDENCE_LABELS[Evidence.CROSS_CHECKED] },
		{ value: 'proven', label: EVIDENCE_LABELS[Evidence.PROVEN] },
		{ value: 'noinfo', label: 'Hide info' }
	];

	let quick = $derived(
		[
			(query.newOnly || tokenize(query.search).includes(NEW_TOKEN)) && 'new',
			query.kevOnly && 'kev',
			query.cveOnly && 'cve',
			query.corroboratedOnly && 'corroborated',
			query.provenOnly && 'proven',
			!query.includeInfo && 'noinfo'
		].filter((v): v is string => !!v)
	);

	function setQuick(values: string[]) {
		// one New filter: the is:new token the tab strip and the IPs bar use
		const search = values.includes('new')
			? appendToken(query.search, NEW_TOKEN)
			: tokenize(query.search)
					.filter((t) => t !== NEW_TOKEN)
					.join(' ');
		onQuery({
			...query,
			search,
			newOnly: false,
			kevOnly: values.includes('kev'),
			cveOnly: values.includes('cve'),
			corroboratedOnly: values.includes('corroborated'),
			provenOnly: values.includes('proven'),
			includeInfo: !values.includes('noinfo')
		});
	}

	function options(list: VulnFacetSet[keyof VulnFacetSet]): Facet[] {
		return list.map((f) => ({ value: f.name, label: f.label ?? f.name, count: f.count }));
	}

	function setList<K extends 'templates' | 'tags' | 'hosts' | 'protocols' | 'scanners'>(
		key: K,
		value: string[]
	) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
		{#if facets.template.length || !facetsLoaded}
			<FacetedFilter
				title="Check"
				options={options(facets.template)}
				selected={query.templates}
				onChange={(v) => setList('templates', v)}
				disabled={!facetsLoaded}
			/>
		{/if}
		{#if facets.tag.length || !facetsLoaded}
			<FacetedFilter
				title="Category"
				options={options(facets.tag)}
				selected={query.tags}
				onChange={(v) => setList('tags', v)}
				disabled={!facetsLoaded}
			/>
		{/if}
		{#if facets.host.length || !facetsLoaded}
			<FacetedFilter
				title="Web asset"
				options={options(facets.host)}
				selected={query.hosts}
				onChange={(v) => setList('hosts', v)}
				disabled={!facetsLoaded}
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
		<ScrollArea
			orientation="horizontal"
			class="max-lg:max-w-full max-lg:min-w-0"
			scrollbarXClasses="h-1"
		>
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
		</ScrollArea>
	</div>

	<div class="ml-auto flex min-w-0 flex-wrap items-center gap-2">
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
			{onShortcuts}
		/>
	</div>
</div>
