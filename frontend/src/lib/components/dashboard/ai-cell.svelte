<script lang="ts">
	import { useScopedRoutes } from './scope-links';
	import Cell from './cell.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { AI_ICON, AI_MODEL_FIELD, AI_YES, aiQuery } from '$lib/config/ai-services';
	import type { AiSummary } from '$lib/utilities/scan-insights';

	const routes = useScopedRoutes();

	interface Props {
		ai: AiSummary | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { ai, scanId = null, loading = false, class: className = '' }: Props = $props();

	const TOP = 7;
	const SERVICES = SURFACE[SurfaceDimension.SERVICES];
	const link = (query: string) =>
		routes.results(SERVICES.tab, scanId, { [SERVICES.queryParam]: query });
	let rows = $derived<BarRow[]>(
		(ai?.services ?? []).slice(0, TOP).map((s) => ({
			key: s.key,
			label: s.label,
			count: s.count,
			href: link(s.query)
		}))
	);
</script>

<Cell
	id="ai"
	description="Services per product"
	href={link(aiQuery(AI_YES))}
	hrefLabel={aiQuery(AI_YES)}
	loading={loading && !ai}
	class={className}
>
	{#if rows.length}
		<RankedBars {rows}>
			{#snippet icon(r)}
				<TechIcon name={r.label} class="size-4">
					{#snippet fallback()}
						<AI_ICON class="size-3.5 text-muted-foreground" />
					{/snippet}
				</TechIcon>
			{/snippet}
		</RankedBars>
	{:else}
		<span class="text-sm text-muted-foreground">No AI service</span>
	{/if}
	{#snippet footer()}
		{#if ai}
			<span>
				{#if ai.models_listed}
					<a href={link(`${AI_MODEL_FIELD}:${AI_YES}`)} class="hover:text-foreground">
						{ai.models_listed.toLocaleString()} listing models</a
					> ·
				{/if}
				{ai.evaluated.toLocaleString()} checked
			</span>
		{/if}
	{/snippet}
</Cell>
