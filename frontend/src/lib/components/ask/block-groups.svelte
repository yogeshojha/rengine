<script lang="ts">
	import { linkScan } from './link-scope';
	import RankedBars, { type BarRow } from '$lib/components/dashboard/ranked-bars.svelte';
	import { QUERY_SCHEMAS } from '$lib/stores/query-schema.svelte';
	import type { SurfaceDimension } from '$lib/config/surface';
	import { blockHref, groupQuery } from './block-columns';
	import type { BlockGroup } from '$lib/types/ask';

	interface Props {
		dimension: string;
		groupBy: string | null;
		query: string | null;
		groups: BlockGroup[];
		scopeValues: string[] | null;
	}

	let { dimension, groupBy, query, groups, scopeValues }: Props = $props();

	const scan = linkScan();

	let schema = $derived(QUERY_SCHEMAS[dimension as SurfaceDimension]);
	let label = $derived(
		schema?.schema.group_dimensions.find((g) => g.key === groupBy)?.label ?? groupBy ?? ''
	);

	$effect(() => {
		void schema?.load();
	});

	let rows = $derived<BarRow[]>(
		groups.map((g) => ({
			key: g.value,
			label: g.label || g.value,
			count: g.count,
			href: blockHref(dimension, groupQuery(query, g.query), scopeValues, scan()) ?? undefined
		}))
	);
</script>

<div class="flex flex-col gap-2 px-4 py-3">
	{#if label}
		<span class="text-2xs font-medium tracking-wide text-muted-foreground uppercase"
			>By {label}</span
		>
	{/if}
	<RankedBars {rows} />
</div>
