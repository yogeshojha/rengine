<script lang="ts">
	import Layers from '@lucide/svelte/icons/layers';
	import Cell from './cell.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { exactToken, type Facet } from '$lib/utilities/scan-insights';

	interface Props {
		tech: Facet[] | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { tech, scanId = null, loading = false, class: className = '' }: Props = $props();

	const TOP = 7;
	const SPEC = SURFACE[SurfaceDimension.WEB_ASSETS];
	let rows = $derived<BarRow[]>(
		(tech ?? []).slice(0, TOP).map((f) => ({
			key: f.value,
			label: f.label,
			count: f.count,
			href: ROUTES.results(SPEC.tab, scanId, { [SPEC.queryParam]: exactToken('tech', f.value) })
		}))
	);
</script>

<Cell
	id="tech"
	title="Technology"
	description="Web assets per technology"
	href={ROUTES.results(SPEC.tab, scanId)}
	hrefLabel={SPEC.label}
	loading={loading && !tech}
	class={className}
>
	<RankedBars {rows} dense>
		{#snippet icon(r)}
			<TechIcon name={r.key} class="size-4">
				{#snippet fallback()}
					<Layers class="size-3.5 text-muted-foreground" />
				{/snippet}
			</TechIcon>
		{/snippet}
	</RankedBars>
	{#snippet footer()}
		{#if tech && tech.length > TOP}
			<span>{tech.length - TOP} more technologies</span>
		{/if}
	{/snippet}
</Cell>
