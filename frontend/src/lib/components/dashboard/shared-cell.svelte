<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { CorrelationGraph } from '$lib/types/correlation';

	interface Props {
		graph: CorrelationGraph | null;
		loading?: boolean;
		class?: string;
	}

	let { graph, loading = false, class: className = '' }: Props = $props();

	const TOP = 6;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	let labels = $derived(new SvelteMap((graph?.kinds ?? []).map((k) => [k.key, k.label])));
	let hubs = $derived(
		(graph?.hubs ?? [])
			.filter((h) => h.targets > 1 && !h.platform)
			.sort((a, b) => b.targets - a.targets || b.count - a.count)
			.slice(0, TOP)
	);
	let spanning = $derived((graph?.hubs ?? []).filter((h) => h.targets > 1 && !h.platform).length);
</script>

<Cell
	id="shared"
	title="Shared across targets"
	href={ROUTES.correlation}
	hrefLabel="Correlation"
	loading={loading && !graph}
	class={className}
>
	{#if hubs.length}
		<ul class="flex flex-col gap-1.5">
			{#each hubs as h (h.id)}
				<li>
					<a
						href={ROUTES.surface(WEB.tab, { [WEB.queryParam]: h.query })}
						class="grid grid-cols-[4.5rem_minmax(0,1fr)_auto] items-baseline gap-2.5 text-xs hover:text-foreground"
					>
						<span class="truncate text-2xs text-muted-foreground"
							>{labels.get(h.kind) ?? h.kind}</span
						>
						<Hint text={h.value}>
							{#snippet child(props)}
								<span {...props} class="block min-w-0 truncate font-mono">{h.label || h.value}</span
								>
							{/snippet}
						</Hint>
						<span class="text-2xs whitespace-nowrap text-muted-foreground tabular-nums">
							{h.targets} targets · {h.count.toLocaleString()}
						</span>
					</a>
				</li>
			{/each}
		</ul>
	{:else}
		<span class="text-sm text-muted-foreground">No shared identity</span>
	{/if}
	{#snippet footer()}
		{#if graph}
			<span>{spanning} hubs · {graph.shared_hosts.toLocaleString()} web assets</span>
		{/if}
	{/snippet}
</Cell>
