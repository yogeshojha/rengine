<script lang="ts">
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { Facet } from '$lib/utilities/scan-insights';
	import { HOSTING_QUERIES, type HostingSplit } from '$lib/types/dashboard';
	import { FRONTING_FILL } from '$lib/config/hosting';

	interface Props {
		hosting: HostingSplit | null;
		networks: Facet[] | null;
		loading?: boolean;
		class?: string;
	}

	let { hosting, networks, loading = false, class: className = '' }: Props = $props();

	const TOP = 4;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const IPS = SURFACE[SurfaceDimension.IPS];
	const capped = (q: string) => hosting?.capped?.[q] ?? false;
	const reads = (n: number, q: string) => `${n.toLocaleString()}${capped(q) ? '+' : ''}`;

	let segments = $derived(
		hosting
			? [
					{
						key: 'edge',
						label: 'Edge',
						n: hosting.edge,
						color: FRONTING_FILL.edge,
						q: HOSTING_QUERIES.edge
					},
					{
						key: 'cloud',
						label: 'Cloud',
						n: hosting.cloud,
						color: FRONTING_FILL.cloud,
						q: HOSTING_QUERIES.cloud
					},
					{
						key: 'direct',
						label: 'Direct',
						n: hosting.direct,
						color: FRONTING_FILL.direct,
						q: HOSTING_QUERIES.direct
					}
				].filter((s) => s.n > 0)
			: []
	);
	let resolved = $derived(hosting?.resolved ?? 0);
	let rows = $derived<BarRow[]>(
		(networks ?? []).slice(0, TOP).map((f) => ({
			key: f.value,
			label: f.label,
			sub: `AS${f.value}`,
			count: f.count,
			href: ROUTES.surface(IPS.tab, { [IPS.queryParam]: `asn:${f.value}` })
		}))
	);
</script>

<Cell
	id="hosting"
	title="Hosting"
	description="By fronting and network"
	href={ROUTES.surface(WEB.tab, { [WEB.queryParam]: HOSTING_QUERIES.resolved })}
	hrefLabel="is:resolved"
	loading={loading && !hosting}
	class={className}
>
	{#if segments.length}
		<div class="flex h-2 w-full gap-0.5 overflow-hidden rounded-full bg-muted">
			{#each segments as s (s.key)}
				<Hint text="{reads(s.n, s.q)} web assets · {s.label}">
					{#snippet child(props)}
						<a
							{...props}
							href={ROUTES.surface(WEB.tab, { [WEB.queryParam]: s.q })}
							class="block h-full transition-opacity hover:opacity-80"
							style="width:{(s.n / Math.max(1, resolved)) * 100}%;background:{s.color}"
							aria-label="{s.label}: {s.n}"
						></a>
					{/snippet}
				</Hint>
			{/each}
		</div>
		<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
			{#each segments as s (s.key)}
				<a
					href={ROUTES.surface(WEB.tab, { [WEB.queryParam]: s.q })}
					class="flex items-center gap-1.5 hover:text-foreground"
				>
					<span class="size-2.5 rounded-[2px]" style="background:{s.color}"></span>
					{s.label}
					<span class="font-medium text-foreground tabular-nums">{reads(s.n, s.q)}</span>
				</a>
			{/each}
		</div>
	{/if}
	{#if rows.length}
		<RankedBars {rows} dense />
	{/if}
	{#snippet footer()}
		{#if hosting}
			<span>{reads(resolved, HOSTING_QUERIES.resolved)} resolving web assets</span>
		{/if}
	{/snippet}
</Cell>
