<script lang="ts">
	import { appendToken, tokenize } from '$lib/utilities/scan-insights';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import ChartGantt from '@lucide/svelte/icons/chart-gantt';
	import {
		SERVICE_MODE_LABELS,
		SERVICES_TIMELINE_VIEW,
		ServiceTimelineMode,
		TIMELINE_WINDOWS
	} from '$lib/config/timeline';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
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
		folded?: string[];
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
		onShortcuts?: () => void;
		/** the Timeline view is offered */
		timeline?: boolean;
		view?: string;
		onView?: (v: string) => void;
		timelineWindow?: number;
		onTimelineWindow?: (scans: number) => void;
		mode?: ServiceTimelineMode;
		onMode?: (mode: ServiceTimelineMode) => void;
	}

	let {
		query,
		facets,
		onQuery,
		dimensions,
		columns,
		visible,
		folded = [],
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
		exportFilters = {},
		onShortcuts,
		timeline = false,
		view = 'table',
		onView,
		timelineWindow = TIMELINE_WINDOWS[1],
		onTimelineWindow,
		mode = ServiceTimelineMode.ADDRESS,
		onMode
	}: Props = $props();

	const NEW_TOKEN = 'is:new';

	const QUICK = [
		{ value: 'new', label: 'New' },
		{ value: 'sensitive', label: 'Sensitive' },
		{ value: 'nonweb', label: 'Non-web' },
		{ value: 'named', label: 'Identified' },
		{ value: 'nocdn', label: 'No CDN' }
	];

	let quick = $derived(
		[
			(query.newOnly || tokenize(query.search).includes(NEW_TOKEN)) && 'new',
			query.sensitiveOnly && 'sensitive',
			query.http === 'no' && 'nonweb',
			query.namedOnly && 'named',
			query.cdn === 'no' && 'nocdn'
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
		{#if timeline}
			<ToggleGroup.Root
				type="single"
				variant="outline"
				value={view}
				onValueChange={(v) => v && onView?.(v)}
				aria-label="View"
			>
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<ToggleGroup.Item {...props} value="table" aria-label="Table view" class="h-9 px-3">
								<Rows3 class="h-4 w-4" />
							</ToggleGroup.Item>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Table view</Tooltip.Content>
				</Tooltip.Root>
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<ToggleGroup.Item
								{...props}
								value={SERVICES_TIMELINE_VIEW}
								aria-label="Timeline view"
								class="h-9 px-3"
							>
								<ChartGantt class="h-4 w-4" />
							</ToggleGroup.Item>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Timeline view</Tooltip.Content>
				</Tooltip.Root>
			</ToggleGroup.Root>
			{#if view === SERVICES_TIMELINE_VIEW}
				<ToggleGroup.Root
					type="single"
					variant="outline"
					value={mode}
					onValueChange={(v) => v && onMode?.(v as ServiceTimelineMode)}
					aria-label="Rows"
				>
					{#each Object.values(ServiceTimelineMode) as m (m)}
						<ToggleGroup.Item value={m} class="h-9 px-3 text-sm font-normal">
							{SERVICE_MODE_LABELS[m]}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
				<div class="flex items-center gap-2 text-sm text-muted-foreground">
					<span>Last</span>
					<ToggleGroup.Root
						type="single"
						variant="outline"
						value={String(timelineWindow)}
						onValueChange={(v) => v && onTimelineWindow?.(Number(v))}
						aria-label="Scans shown"
					>
						{#each TIMELINE_WINDOWS as n (n)}
							<ToggleGroup.Item
								value={String(n)}
								aria-label="Last {n} scans"
								class="h-9 px-3 text-sm font-normal tabular-nums"
							>
								{n}
							</ToggleGroup.Item>
						{/each}
					</ToggleGroup.Root>
					<span>scans</span>
				</div>
			{/if}
		{/if}
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
			{folded}
			{onToggleColumn}
			{density}
			{onDensity}
			{refreshing}
			{onRefresh}
			{projectId}
			{scanId}
			{exportFilters}
			{onShortcuts}
		/>
	</div>
</div>
