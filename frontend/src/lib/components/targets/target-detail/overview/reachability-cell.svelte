<script lang="ts" module>
	import { CHART_FILL } from '$lib/components/scans/results/overview/palette';

	export interface ReachabilityState {
		key: string;
		label: string;
		query: string;
		fill: string;
		reachable?: boolean;
	}

	const SERIES_FADED = 'color-mix(in oklch, var(--series) 35%, var(--muted))';

	export function reachabilityStates(isDomain: boolean): ReachabilityState[] {
		const out: ReachabilityState[] = [];
		if (isDomain)
			out.push({
				key: 'unresolved',
				label: 'Unresolved',
				query: 'not is:resolved and not is:web',
				fill: CHART_FILL.muted
			});
		out.push(
			{
				key: 'no_http',
				label: 'No HTTP response',
				query: isDomain ? 'is:resolved and not is:web' : 'not is:web',
				fill: isDomain ? SERIES_FADED : CHART_FILL.muted
			},
			{
				key: 'web',
				label: 'Answers HTTP',
				query: 'is:web and not is:vulnerable',
				fill: 'var(--series)',
				reachable: true
			},
			{
				key: 'finding',
				label: 'With a finding',
				query: 'is:web and is:vulnerable',
				fill: 'var(--destructive)',
				reachable: true
			}
		);
		return out;
	}
</script>

<script lang="ts">
	import { goto } from '$app/navigation';
	import Cell from '$lib/components/cell.svelte';
	import CompositionBar from '$lib/components/scans/results/overview/composition-bar.svelte';
	import type { Segment } from '$lib/components/scans/results/overview/composition-bar.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { formatShortDate } from '$lib/utilities/dates';

	interface Props {
		counts: Record<string, number>;
		capped?: Record<string, boolean>;
		rowCount?: number | null;
		isDomain: boolean;
		scanId: string;
		observedAt?: string | null;
		loading?: boolean;
		class?: string;
	}

	let {
		counts,
		capped = {},
		rowCount = null,
		isDomain,
		scanId,
		observedAt = null,
		loading = false,
		class: className = ''
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const link = (q?: string) =>
		ROUTES.results(WEB.tab, scanId, q ? { [WEB.queryParam]: q } : undefined);

	let states = $derived(reachabilityStates(isDomain));
	let exact = $derived.by(() => {
		const over = states.filter((s) => capped[s.query]);
		if (over.length !== 1 || rowCount == null) return counts;
		const rest = states.reduce((n, s) => (capped[s.query] ? n : n + (counts[s.query] ?? 0)), 0);
		const q = over[0].query;
		return { ...counts, [q]: Math.max(rowCount - rest, counts[q] ?? 0) };
	});
	let total = $derived(states.reduce((n, s) => n + (exact[s.query] ?? 0), 0));
	let segments = $derived<Segment[]>(
		states
			.map((s) => ({
				key: s.key,
				label: s.label,
				count: exact[s.query] ?? 0,
				color: s.fill,
				filter: s.query
			}))
			.filter((s) => s.count > 0)
	);
	let reachable = $derived(
		states.filter((s) => s.reachable).reduce((n, s) => n + (exact[s.query] ?? 0), 0)
	);
</script>

<Cell
	skeleton="meters"
	id="reachability"
	title="Reachability"
	description={observedAt ? `From the ${formatShortDate(observedAt)} run` : undefined}
	href={link()}
	hrefLabel="{total.toLocaleString()} {WEB.nounPlural}"
	loading={loading && !total}
	class={className}
>
	{#if total > 0}
		<CompositionBar
			{segments}
			{total}
			label="Reachability"
			inline
			onSelect={(q) => goto(link(q))}
		/>
	{:else}
		<span class="text-sm text-muted-foreground">Not scanned</span>
	{/if}
	{#snippet footer()}
		{#if total > 0}
			<span>
				{reachable.toLocaleString()} of {total.toLocaleString()} answer HTTP
			</span>
		{/if}
	{/snippet}
</Cell>
