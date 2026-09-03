<script lang="ts">
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Image from '@lucide/svelte/icons/image';
	import X from '@lucide/svelte/icons/x';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Toggle } from '$lib/components/ui/toggle';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import FacetedFilter from '../faceted-filter.svelte';
	import {
		activeFacetCount,
		emptyQuery,
		queryChips,
		type SubdomainFacetSet,
		type WebAssetQuery
	} from '$lib/utilities/scan-insights';

	export interface ColumnDef {
		key: string;
		label: string;
	}

	interface Props {
		query: WebAssetQuery;
		facets: SubdomainFacetSet;
		onQuery: (q: WebAssetQuery) => void;
		total: number;
		scanTotal: number;
		view: string;
		onView: (v: string) => void;
		columns: ColumnDef[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
		onlyShots: boolean;
		onOnlyShots: (v: boolean) => void;
	}

	let {
		query,
		facets,
		onQuery,
		total,
		scanTotal,
		view,
		onView,
		columns,
		visible,
		onToggleColumn,
		density,
		onDensity,
		onlyShots,
		onOnlyShots
	}: Props = $props();

	const QUICK = [
		{ value: 'live', label: 'Live' },
		{ value: 'new', label: 'New' },
		{ value: 'issues', label: 'Issues' },
		{ value: 'nowaf', label: 'No WAF' }
	];

	let quick = $derived(
		[
			query.liveOnly && 'live',
			query.newOnly && 'new',
			query.issuesOnly && 'issues',
			query.waf === 'none' && 'nowaf'
		].filter((v): v is string => !!v)
	);
	let chips = $derived(queryChips(query));
	let dirty = $derived(activeFacetCount(query) > 0 || !!query.search);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			liveOnly: values.includes('live'),
			newOnly: values.includes('new'),
			issuesOnly: values.includes('issues'),
			waf: values.includes('nowaf') ? 'none' : query.waf === 'none' ? 'any' : query.waf
		});
	}
	function setList<K extends 'status' | 'tech' | 'service' | 'cert' | 'source'>(
		key: K,
		value: string[]
	) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-col gap-2">
	<div class="flex flex-wrap items-center gap-2">
		<FacetedFilter
			title="Status"
			options={facets.status}
			selected={query.status}
			onChange={(v) => setList('status', v)}
		/>
		<FacetedFilter
			title="Tech"
			options={facets.tech}
			selected={query.tech}
			onChange={(v) => setList('tech', v)}
		/>
		<FacetedFilter
			title="Service"
			options={facets.service}
			selected={query.service}
			onChange={(v) => setList('service', v)}
		/>
		{#if facets.cert.length}
			<FacetedFilter
				title="Cert"
				options={facets.cert}
				selected={query.cert}
				onChange={(v) => setList('cert', v)}
			/>
		{/if}
		<FacetedFilter
			title="Source"
			options={facets.source}
			selected={query.source}
			onChange={(v) => setList('source', v)}
		/>

		<Separator orientation="vertical" class="mx-0.5 h-5" />

		<ToggleGroup.Root
			type="multiple"
			value={quick}
			onValueChange={setQuick}
			variant="outline"
			size="sm"
		>
			{#each QUICK as q (q.value)}
				<ToggleGroup.Item value={q.value} class="px-2.5 text-xs">{q.label}</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>

		{#if dirty}
			<Button
				variant="ghost"
				size="sm"
				class="h-8 text-muted-foreground"
				onclick={() => onQuery(emptyQuery())}
			>
				Reset <X data-icon="inline-end" />
			</Button>
		{/if}

		<div class="ml-auto flex items-center gap-2">
			<span class="text-xs text-muted-foreground tabular-nums">
				{total.toLocaleString()}{scanTotal && scanTotal !== total
					? ` of ${scanTotal.toLocaleString()}`
					: ''} hosts
			</span>
			{#if view === 'gallery'}
				<Toggle
					pressed={onlyShots}
					onPressedChange={onOnlyShots}
					variant="outline"
					size="sm"
					class="h-8 gap-1.5 text-xs"
					aria-label="Only hosts with a screenshot"
				>
					<Image class="size-3.5" />
					With screenshot
				</Toggle>
			{/if}
			<ToggleGroup.Root
				type="single"
				value={view}
				onValueChange={(v) => v && onView(v)}
				variant="outline"
				size="sm"
			>
				<ToggleGroup.Item value="table" aria-label="Table view" title="Table view">
					<Rows3 class="size-4" />
				</ToggleGroup.Item>
				<ToggleGroup.Item value="gallery" aria-label="Gallery view" title="Gallery view">
					<LayoutGrid class="size-4" />
				</ToggleGroup.Item>
			</ToggleGroup.Root>
			{#if view === 'table'}
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button variant="outline" size="sm" class="h-8" {...props}>
								<Columns3 data-icon="inline-start" /> Columns
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
		</div>
	</div>

	{#if chips.length}
		<div class="flex flex-wrap items-center gap-1.5">
			{#each chips as chip (chip.id)}
				<Badge variant="secondary" class="gap-1 pr-1 font-normal">
					{chip.label}
					<button
						type="button"
						class="rounded-sm text-muted-foreground hover:text-foreground"
						aria-label="Remove filter {chip.label}"
						onclick={() => onQuery(chip.remove(query))}
					>
						<X class="size-3" />
					</button>
				</Badge>
			{/each}
		</div>
	{/if}
</div>
