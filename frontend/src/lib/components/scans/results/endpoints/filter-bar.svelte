<script lang="ts">
	import Layers from '@lucide/svelte/icons/layers';
	import Network from '@lucide/svelte/icons/network';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import ChevronsDownUp from '@lucide/svelte/icons/chevrons-down-up';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import ViewControls from '../table/view-controls.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';
	import { EndpointSource } from '$lib/config/endpoints';
	import type { EndpointFacetSet, EndpointQuery, EndpointView } from '$lib/utilities/endpoints';

	interface Props {
		query: EndpointQuery;
		facets: EndpointFacetSet;
		onQuery: (q: EndpointQuery) => void;
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
		view: EndpointView;
		onView: (v: EndpointView) => void;
		inHost?: boolean;
		hideStatic: boolean;
		onHideStatic: (v: boolean) => void;
		hideRootOnly?: boolean;
		onHideRootOnly?: (v: boolean) => void;
		expandedCount?: number;
		onCollapseAll?: () => void;
		goneCount?: number;
		goneLens?: boolean;
		onGoneLens?: (on: boolean) => void;
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
		view,
		onView,
		inHost = false,
		hideStatic,
		onHideStatic,
		hideRootOnly = false,
		onHideRootOnly,
		expandedCount = 0,
		onCollapseAll,
		goneCount = 0,
		goneLens = false,
		onGoneLens,
		projectId = '',
		scanId = '',
		exportFilters = {}
	}: Props = $props();

	const LENSES: { value: EndpointView; label: string; hint: string; icon: typeof Network }[] = [
		{
			value: 'hosts',
			label: 'Hosts',
			hint: 'Every host, ranked',
			icon: Network
		},
		{
			value: 'merged',
			label: 'Across hosts',
			hint: 'Paths merged across hosts',
			icon: Layers
		},
		{ value: 'list', label: 'List', hint: 'One flat list', icon: Rows3 }
	];

	let hasProxy = $derived(facets.source.some((f) => f.value === EndpointSource.PROXY));
	let hostsAtRest = $derived(view === 'hosts' && !inHost);
	let quickOptions = $derived(
		[
			{ value: 'new', label: 'New' },
			{ value: 'unverified', label: 'Not checked' },
			hasProxy ? { value: 'browsed', label: 'Browsed' } : null,
			hasProxy ? { value: 'unbrowsed', label: 'Not browsed' } : null,
			{ value: 'static', label: 'Hide static' },
			hostsAtRest && onHideRootOnly ? { value: 'rootonly', label: 'Hide root-only' } : null
		].filter((q): q is { value: string; label: string } => q !== null)
	);
	let quick = $derived(
		[
			query.newOnly && 'new',
			query.probed === 'no' && 'unverified',
			query.browsed === 'yes' && 'browsed',
			query.browsed === 'no' && 'unbrowsed',
			hideStatic && 'static',
			hideRootOnly && hostsAtRest && 'rootonly'
		].filter((v): v is string => !!v)
	);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			newOnly: values.includes('new'),
			probed: values.includes('unverified') ? 'no' : 'any',
			browsed: values.includes('browsed') ? 'yes' : values.includes('unbrowsed') ? 'no' : 'any'
		});
		onHideStatic(values.includes('static'));
		if (hostsAtRest) onHideRootOnly?.(values.includes('rootonly'));
	}

	function pick(key: 'source' | 'interest' | 'statusClass', value: string) {
		onQuery({ ...query, [key]: query[key] === value ? '' : value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
		{#if facets.source.length > 1}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-9 gap-2 {query.source ? 'border-primary/50 bg-primary/5' : ''}"
						>
							Found by
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-56 overflow-visible">
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
						{#each facets.source as f (f.value)}
							<DropdownMenu.CheckboxItem
								checked={query.source === f.value}
								onCheckedChange={() => pick('source', f.value)}
								closeOnSelect={false}
							>
								<span class="flex-1">{f.label}</span>
								<span class="tabular-nums text-muted-foreground">{f.count}</span>
							</DropdownMenu.CheckboxItem>
						{/each}
					</ScrollArea>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		{#if facets.interest.length}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-9 gap-2 {query.interest ? 'border-primary/50 bg-primary/5' : ''}"
						>
							Interest
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-64 overflow-visible">
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
						{#each facets.interest as f (f.value)}
							<DropdownMenu.CheckboxItem
								checked={query.interest === f.value}
								onCheckedChange={() => pick('interest', f.value)}
								closeOnSelect={false}
							>
								<span class="flex-1">{f.label}</span>
								<span class="tabular-nums text-muted-foreground">{f.count}</span>
							</DropdownMenu.CheckboxItem>
						{/each}
					</ScrollArea>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		{#if facets.status_class.length > 1}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-9 gap-2 {query.statusClass ? 'border-primary/50 bg-primary/5' : ''}"
						>
							Status
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-52 overflow-visible">
					{#each facets.status_class as f (f.value)}
						<DropdownMenu.CheckboxItem
							checked={query.statusClass === f.value}
							onCheckedChange={() => pick('statusClass', f.value)}
							closeOnSelect={false}
						>
							<span class="flex-1">{f.label}</span>
							<span class="tabular-nums text-muted-foreground">{f.count}</span>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		<ToggleGroup.Root
			type="multiple"
			value={quick}
			onValueChange={setQuick}
			variant="outline"
			aria-label="Quick filters"
		>
			{#each quickOptions as q (q.value)}
				<ToggleGroup.Item value={q.value} class="h-9 px-3 text-sm font-normal">
					{q.label}
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>

		{#if goneCount > 0 && onGoneLens}
			<Hint text="Endpoints in the previous scan and not in this one">
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<ToggleGroup.Root
							type="single"
							value={goneLens ? 'gone' : ''}
							onValueChange={(v) => onGoneLens(v === 'gone')}
							variant="outline"
							aria-label="Gone since the previous scan"
						>
							<ToggleGroup.Item value="gone" class="h-9 gap-1.5 px-3 text-sm font-normal">
								Gone
								<span class="text-xs tabular-nums text-muted-foreground">
									{goneCount.toLocaleString()}
								</span>
							</ToggleGroup.Item>
						</ToggleGroup.Root>
					</span>
				{/snippet}
			</Hint>
		{/if}
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<ToggleGroup.Root
			type="single"
			value={view}
			onValueChange={(v) => v && onView(v as EndpointView)}
			variant="outline"
			aria-label="View"
		>
			{#each LENSES as lens (lens.value)}
				<Hint text={lens.hint}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<ToggleGroup.Item value={lens.value} class="h-9 gap-1.5 px-3" aria-label={lens.label}>
								<lens.icon class="size-4" />
								<span class="hidden text-sm font-normal lg:inline">{lens.label}</span>
							</ToggleGroup.Item>
						</span>
					{/snippet}
				</Hint>
			{/each}
		</ToggleGroup.Root>

		{#if view !== 'list' && expandedCount > 0 && onCollapseAll}
			<Hint text="Collapse all folders">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon"
						class="h-9 w-9"
						aria-label="Collapse all"
						onclick={onCollapseAll}
					>
						<ChevronsDownUp class="h-4 w-4" />
					</Button>
				{/snippet}
			</Hint>
		{/if}

		<ViewControls
			dimension={SurfaceDimension.ENDPOINTS}
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
			showGroupBy={view === 'list'}
		/>
	</div>
</div>
