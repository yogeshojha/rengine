<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import Widget from './widget.svelte';
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

	const TOP = 5;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const IPS = SURFACE[SurfaceDimension.IPS];
	const capped = (q: string) => hosting?.capped?.[q] ?? false;
	const reads = (n: number, q: string) => `${n.toLocaleString()}${capped(q) ? '+' : ''}`;

	let segments = $derived(
		hosting
			? [
					{
						key: 'edge',
						label: 'CDN or WAF edge',
						n: hosting.edge,
						color: FRONTING_FILL.edge,
						q: HOSTING_QUERIES.edge
					},
					{
						key: 'cloud',
						label: 'Cloud provider',
						n: hosting.cloud,
						color: FRONTING_FILL.cloud,
						q: HOSTING_QUERIES.cloud
					},
					{
						key: 'direct',
						label: 'Direct to origin',
						n: hosting.direct,
						color: FRONTING_FILL.direct,
						q: HOSTING_QUERIES.direct
					}
				].filter((s) => s.n > 0)
			: []
	);
	let resolved = $derived(hosting?.resolved ?? 0);
	let exact = $derived(
		!!hosting && !capped(HOSTING_QUERIES.resolved) && !segments.some((s) => capped(s.q))
	);
	let rows = $derived<BarRow[]>(
		(networks ?? []).slice(0, TOP).map((f) => ({
			key: f.value,
			label: f.label,
			count: f.count,
			href: ROUTES.surface(IPS.tab, { [IPS.queryParam]: `asn:${f.value}` })
		}))
	);
</script>

<Widget
	title="Hosting"
	description="By fronting and network"
	href={ROUTES.surface(WEB.tab, { [WEB.queryParam]: HOSTING_QUERIES.resolved })}
	hrefLabel="Resolving"
	loading={loading && !hosting}
	class={className}
>
	<div class="flex flex-col gap-4 px-5 py-4">
		{#if segments.length}
			<div class="flex flex-col gap-2">
				<div class="flex h-2.5 w-full gap-px overflow-hidden rounded-full bg-muted">
					{#each segments as s (s.key)}
						<Hint text="{reads(s.n, s.q)} {s.n === 1 ? 'web asset' : 'web assets'} · {s.label}">
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
				<ul class="flex flex-col gap-1">
					{#each segments as s (s.key)}
						<li>
							<a
								href={ROUTES.surface(WEB.tab, { [WEB.queryParam]: s.q })}
								class="flex items-center gap-2 text-sm hover:text-foreground"
							>
								<span class="size-2.5 shrink-0 rounded-[3px]" style="background:{s.color}"></span>
								<span class="min-w-0 flex-1 truncate text-muted-foreground">{s.label}</span>
								<span class="font-medium tabular-nums">{reads(s.n, s.q)}</span>
								{#if exact}
									<span class="w-9 text-right text-2xs text-muted-foreground tabular-nums">
										{resolved ? Math.round((s.n / resolved) * 100) : 0}%
									</span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
		{#if rows.length}
			<div class="flex flex-col gap-2">
				<span class="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
					Top networks by address
				</span>
				<RankedBars {rows} dense />
			</div>
		{/if}
	</div>
	{#snippet footer()}
		{#if hosting}
			{reads(resolved, HOSTING_QUERIES.resolved)} resolving {resolved === 1
				? 'web asset'
				: 'web assets'}
		{/if}
	{/snippet}
</Widget>
