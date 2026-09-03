<script lang="ts">
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Layers from '@lucide/svelte/icons/layers';
	import X from '@lucide/svelte/icons/x';
	import Image from '@lucide/svelte/icons/image';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Toggle } from '$lib/components/ui/toggle';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { Button } from '$lib/components/ui/button';
	import FacetedFilter from '../faceted-filter.svelte';
	import SortMenu from './sort-menu.svelte';
	import type { WebAssetColumn } from './columns';
	import type { SubdomainFacetSet, WebAssetQuery } from '$lib/utilities/scan-insights';
	import { querySchema } from '$lib/stores/query-schema.svelte';

	interface Props {
		query: WebAssetQuery;
		facets: SubdomainFacetSet;
		onQuery: (q: WebAssetQuery) => void;
		view: string;
		onView: (v: string) => void;
		columns: WebAssetColumn[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
		onlyShots: boolean;
		onOnlyShots: (v: boolean) => void;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		refreshing: boolean;
		onRefresh: () => void;
		groupBy: string;
		onGroupBy: (key: string) => void;
	}

	let {
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
		onOnlyShots,
		sortKey,
		sortDir,
		onSort,
		refreshing,
		onRefresh,
		groupBy,
		onGroupBy
	}: Props = $props();

	let dimensions = $derived(querySchema.schema.group_dimensions);
	let groupLabel = $derived(dimensions.find((d) => d.key === groupBy)?.label ?? 'Group');

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
	function setList<K extends 'tech' | 'service' | 'cert' | 'source'>(key: K, value: string[]) {
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
			aria-label="Quick filters"
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
		{/if}

		{#if dimensions.length}
			<ButtonGroup>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="outline"
								size="sm"
								class="h-9 gap-2 {groupBy ? 'border-primary/50 bg-primary/5' : ''}"
							>
								<Layers class="h-4 w-4" />
								<span class="hidden sm:inline">{groupLabel}</span>
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-52">
						<DropdownMenu.Label>Group by</DropdownMenu.Label>
						<DropdownMenu.Separator />
						<DropdownMenu.RadioGroup value={groupBy} onValueChange={onGroupBy}>
							<DropdownMenu.RadioItem value="">No grouping</DropdownMenu.RadioItem>
							{#each dimensions as dimension (dimension.key)}
								<DropdownMenu.RadioItem value={dimension.key}
									>{dimension.label}</DropdownMenu.RadioItem
								>
							{/each}
						</DropdownMenu.RadioGroup>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
				{#if groupBy}
					<Button
						variant="outline"
						size="icon"
						class="h-9 w-9 border-primary/50 bg-primary/5 text-muted-foreground hover:text-foreground"
						aria-label="Clear grouping"
						onclick={() => onGroupBy('')}
					>
						<X class="h-4 w-4" />
					</Button>
				{/if}
			</ButtonGroup>
		{/if}

		{#if !groupBy}
			<SortMenu {sortKey} {sortDir} {onSort} />
		{/if}

		{#if view === 'table' && !groupBy}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
							<Columns3 class="h-4 w-4" />
							<span class="hidden sm:inline">Columns</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-44">
					<DropdownMenu.Group>
						<DropdownMenu.Label>Columns</DropdownMenu.Label>
						{#each columns as col (col.key)}
							<DropdownMenu.CheckboxItem
								checked={visible.includes(col.key)}
								onCheckedChange={() => onToggleColumn(col.key)}
								closeOnSelect={false}
							>
								{col.label}
							</DropdownMenu.CheckboxItem>
						{/each}
					</DropdownMenu.Group>
					<DropdownMenu.Separator />
					<DropdownMenu.Group>
						<DropdownMenu.Label>Density</DropdownMenu.Label>
						<DropdownMenu.RadioGroup value={density} onValueChange={onDensity}>
							<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
							<DropdownMenu.RadioItem value="cozy">Cozy</DropdownMenu.RadioItem>
						</DropdownMenu.RadioGroup>
					</DropdownMenu.Group>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		<Button
			variant="outline"
			size="icon"
			class="h-9 w-9"
			aria-label="Refresh"
			onclick={onRefresh}
			disabled={refreshing}
		>
			<RefreshCw class="h-4 w-4 {refreshing ? 'animate-spin' : ''}" />
		</Button>
	</div>
</div>
