<script lang="ts">
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Layers from '@lucide/svelte/icons/layers';
	import X from '@lucide/svelte/icons/x';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { Button } from '$lib/components/ui/button';
	import FacetedFilter from '../faceted-filter.svelte';
	import SortMenu from '../table/sort-menu.svelte';
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
		onGroupBy
	}: Props = $props();

	let groupLabel = $derived(dimensions.find((d) => d.key === groupBy)?.label ?? 'Group');

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
					<DropdownMenu.Content align="end" class="w-52">
						<DropdownMenu.Label>Group by</DropdownMenu.Label>
						<DropdownMenu.Separator />
						<DropdownMenu.RadioGroup value={groupBy} onValueChange={onGroupBy}>
							<DropdownMenu.RadioItem value="">No grouping</DropdownMenu.RadioItem>
							{#each dimensions as dimension (dimension.key)}
								<DropdownMenu.RadioItem value={dimension.key}>
									{dimension.label}
								</DropdownMenu.RadioItem>
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
