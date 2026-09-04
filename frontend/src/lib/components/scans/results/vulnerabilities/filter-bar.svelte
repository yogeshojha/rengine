<script lang="ts">
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Layers from '@lucide/svelte/icons/layers';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import FacetedFilter from '../faceted-filter.svelte';
	import SortMenu from '../table/sort-menu.svelte';
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
		columnsLocked = false
	}: Props = $props();

	const QUICK = [
		{ value: 'new', label: 'New' },
		{ value: 'kev', label: 'Known exploited' },
		{ value: 'cve', label: 'Has a CVE' },
		{ value: 'corroborated', label: 'Confirmed' },
		{ value: 'noinfo', label: 'Hide info' },
		{ value: 'reviewed', label: 'Show reviewed' }
	];

	let groupLabel = $derived(dimensions.find((d) => d.key === groupBy)?.label ?? 'Group');

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
					<DropdownMenu.Content align="end" class="max-h-none w-52 overflow-visible">
						<DropdownMenu.Label>Group by</DropdownMenu.Label>
						<DropdownMenu.Separator />
						<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
							<DropdownMenu.RadioGroup value={groupBy} onValueChange={onGroupBy}>
								<DropdownMenu.RadioItem value="">No grouping</DropdownMenu.RadioItem>
								{#each dimensions as dimension (dimension.key)}
									<DropdownMenu.RadioItem value={dimension.key}>
										{dimension.label}
									</DropdownMenu.RadioItem>
								{/each}
							</DropdownMenu.RadioGroup>
						</ScrollArea>
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
			<SortMenu {sorts} {sortKey} {sortDir} {onSort} />

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
							<Columns3 class="h-4 w-4" />
							<span class="hidden sm:inline">Columns</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="max-h-none w-44 overflow-visible">
					{#if !columnsLocked}
						<DropdownMenu.Group>
							<DropdownMenu.Label>Columns</DropdownMenu.Label>
							<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-64">
								{#each columns as col (col.key)}
									<DropdownMenu.CheckboxItem
										checked={visible.includes(col.key)}
										onCheckedChange={() => onToggleColumn(col.key)}
										closeOnSelect={false}
									>
										{col.label}
									</DropdownMenu.CheckboxItem>
								{/each}
							</ScrollArea>
						</DropdownMenu.Group>
						<DropdownMenu.Separator />
					{/if}
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
