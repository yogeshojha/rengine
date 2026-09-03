<script lang="ts">
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import X from '@lucide/svelte/icons/x';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import FacetedFilter from '../faceted-filter.svelte';
	import type { ColumnDef } from '../web-assets/columns';
	import {
		emptyIpQuery,
		ipActiveFacetCount,
		ipQueryChips,
		type IpFacetSet,
		type IpQuery
	} from '$lib/utilities/ip-groups';

	interface Props {
		query: IpQuery;
		facets: IpFacetSet;
		onQuery: (q: IpQuery) => void;
		total: number;
		columns: ColumnDef[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
	}

	let {
		query,
		facets,
		onQuery,
		total,
		columns,
		visible,
		onToggleColumn,
		density,
		onDensity
	}: Props = $props();

	const QUICK = [
		{ value: 'alive', label: 'Responding' },
		{ value: 'hosted', label: 'Has hosts' },
		{ value: 'open', label: 'Open ports' },
		{ value: 'sensitive', label: 'Sensitive' },
		{ value: 'v6', label: 'IPv6' }
	];

	let quick = $derived(
		[
			query.aliveOnly && 'alive',
			query.hostedOnly && 'hosted',
			query.openOnly && 'open',
			query.sensitiveOnly && 'sensitive',
			query.version === 6 && 'v6'
		].filter((v): v is string => !!v)
	);
	let chips = $derived(ipQueryChips(query, facets));
	let dirty = $derived(ipActiveFacetCount(query) > 0 || !!query.search);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			aliveOnly: values.includes('alive'),
			hostedOnly: values.includes('hosted'),
			openOnly: values.includes('open'),
			sensitiveOnly: values.includes('sensitive'),
			version: values.includes('v6') ? 6 : query.version === 6 ? 0 : query.version
		});
	}
	function setList<K extends 'asn' | 'country' | 'port' | 'service'>(key: K, value: string[]) {
		onQuery({ ...query, [key]: value });
	}
</script>

<div class="flex flex-col gap-2">
	<div class="flex flex-wrap items-center gap-2">
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
		{#if facets.asn.length || facets.country.length || facets.port.length || facets.service.length}
			<Separator orientation="vertical" class="mx-0.5 h-5" />
		{/if}

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
				onclick={() => onQuery(emptyIpQuery())}
			>
				Reset <X data-icon="inline-end" />
			</Button>
		{/if}

		<div class="ml-auto flex items-center gap-2">
			<span class="text-xs text-muted-foreground tabular-nums">
				{total.toLocaleString()}
				{total === 1 ? 'address' : 'addresses'}
			</span>
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
