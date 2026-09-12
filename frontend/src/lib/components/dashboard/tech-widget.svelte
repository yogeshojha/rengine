<script lang="ts">
	import Layers from '@lucide/svelte/icons/layers';
	import Widget from './widget.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { exactToken, type Facet } from '$lib/utilities/scan-insights';

	interface Props {
		tech: Facet[] | null;
		loading?: boolean;
		class?: string;
	}

	let { tech, loading = false, class: className = '' }: Props = $props();

	const TOP = 8;
	const SPEC = SURFACE[SurfaceDimension.WEB_ASSETS];

	let rows = $derived<BarRow[]>(
		(tech ?? []).slice(0, TOP).map((f) => ({
			key: f.value,
			label: f.label,
			count: f.count,
			href: ROUTES.surface(SPEC.tab, { [SPEC.queryParam]: exactToken('tech', f.value) })
		}))
	);
</script>

<Widget
	title="Technology"
	description="Technologies fingerprinted on web assets"
	href={ROUTES.surface(SPEC.tab)}
	hrefLabel="Web assets"
	loading={loading && !tech}
	class={className}
>
	<div class="px-5 py-4">
		<RankedBars {rows}>
			{#snippet icon(r)}
				<TechIcon name={r.key} class="size-4">
					{#snippet fallback()}
						<Layers class="size-3.5 text-muted-foreground" />
					{/snippet}
				</TechIcon>
			{/snippet}
		</RankedBars>
	</div>
	{#snippet footer()}
		{#if tech && tech.length > TOP}
			<a href={ROUTES.surface(SPEC.tab)} class="hover:text-foreground hover:underline">
				{tech.length - TOP} more technologies in Web assets
			</a>
		{:else}
			Counts are web assets with the technology
		{/if}
	{/snippet}
</Widget>
