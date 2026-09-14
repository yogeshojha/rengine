<script lang="ts">
	import Cell from './cell.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { SoftwareCoverage, SoftwareFacets } from '$lib/types/software';

	interface Props {
		software: { facets: SoftwareFacets; coverage: SoftwareCoverage } | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { software, scanId = null, loading = false, class: className = '' }: Props = $props();

	const TOP = 6;
	const SPEC = SURFACE[SurfaceDimension.SOFTWARE];
	let rows = $derived<BarRow[]>(
		(software?.facets.product ?? []).slice(0, TOP).map((f) => ({
			key: f.key,
			label: f.label,
			count: f.count,
			href: ROUTES.results(SPEC.tab, scanId, { [SPEC.queryParam]: `product="${f.key}"` })
		}))
	);
	let coverage = $derived(software?.coverage ?? null);
	let mappedShare = $derived(
		coverage && coverage.components ? Math.round((coverage.mapped / coverage.components) * 100) : 0
	);
</script>

<Cell
	id="software"
	title="Software CVEs"
	description="By product"
	href={ROUTES.results(SPEC.tab, scanId)}
	hrefLabel={SPEC.label}
	loading={loading && !software}
	class={className}
>
	{#if rows.length}
		<RankedBars {rows} dense />
	{:else}
		<span class="text-sm text-muted-foreground">No matches</span>
	{/if}
	{#if coverage && coverage.components}
		<div class="flex flex-col gap-1.5">
			<div class="flex h-1.5 gap-0.5 overflow-hidden rounded-full bg-muted">
				<span class="block h-full bg-series" style="width:{mappedShare}%"></span>
			</div>
			<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
				<span class="flex items-center gap-1.5">
					<span class="size-2.5 rounded-[2px] bg-series"></span>
					Mapped products
					<span class="font-medium text-foreground tabular-nums">{mappedShare}%</span>
				</span>
				<span class="flex items-center gap-1.5">
					<span class="size-2.5 rounded-[2px] bg-muted"></span>
					Unmapped
					<span class="font-medium text-foreground tabular-nums"
						>{coverage.unmapped.toLocaleString()}</span
					>
				</span>
			</div>
		</div>
	{/if}
	{#snippet footer()}
		{#if coverage}
			<span>
				{coverage.findings.toLocaleString()} matches on {coverage.matched.toLocaleString()} components{#if coverage.feed_age_hours !== null}
					· corpus {coverage.feed_age_hours < 24
						? `${Math.round(coverage.feed_age_hours)}h`
						: `${Math.round(coverage.feed_age_hours / 24)}d`} old{/if}
			</span>
		{/if}
	{/snippet}
</Cell>
