<script lang="ts">
	import { arc, pie } from 'd3-shape';
	import Cell from './cell.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { SERVICE_CLASS_FILL, SERVICE_CLASS_LABELS } from '$lib/config/service-classes';
	import type { DashboardExposure } from '$lib/types/dashboard';

	interface Props {
		exposure: DashboardExposure;
		scanId?: string | null;
		class?: string;
	}

	let { exposure, scanId = null, class: className = '' }: Props = $props();

	const SIZE = 96;
	const RING = 11;
	const SPEC = SURFACE[SurfaceDimension.SERVICES];
	const TOP = 3;
	const link = (q: string) => ROUTES.results(SPEC.tab, scanId, { [SPEC.queryParam]: q });

	let slices = $derived(exposure.bands.filter((b) => b.count > 0));
	let arcs = $derived.by(() => {
		const layout = pie<{ count: number }>()
			.value((d) => d.count)
			.sort(null)
			.padAngle(0.03);
		const shape = arc<{ startAngle: number; endAngle: number; padAngle: number }>()
			.innerRadius(SIZE / 2 - RING)
			.outerRadius(SIZE / 2)
			.cornerRadius(2);
		return layout(slices).map((a, i) => ({ d: shape(a) ?? '', band: slices[i] }));
	});
	let hovered = $state<string | null>(null);
	let top = $derived<BarRow[]>(
		exposure.top
			.filter((t) => t.sensitive)
			.slice(0, TOP)
			.map((t) => ({
				key: t.key,
				label: t.label,
				count: t.count,
				sub: 'sensitive',
				href: link(t.query),
				tone: 'var(--sev-high)'
			}))
	);
</script>

<Cell
	id="services"
	title="Services"
	description="By class"
	href={ROUTES.results(SPEC.tab, scanId)}
	hrefLabel="{exposure.services.toLocaleString()} services"
	class={className}
>
	<div class="flex items-center gap-4">
		{#if slices.length >= 2}
			<div class="relative shrink-0" style="width:{SIZE}px;height:{SIZE}px">
				<svg viewBox="0 0 {SIZE} {SIZE}" class="size-full">
					<g transform="translate({SIZE / 2},{SIZE / 2})">
						{#each arcs as a (a.band.key)}
							<a
								href={link(a.band.query)}
								aria-label="{a.band.label}: {a.band.count}"
								onmouseenter={() => (hovered = a.band.key)}
								onmouseleave={() => (hovered = null)}
							>
								<path
									d={a.d}
									fill={SERVICE_CLASS_FILL[a.band.key] ?? 'var(--chart-5)'}
									class="transition-opacity"
									style="opacity:{hovered && hovered !== a.band.key ? 0.35 : 1}"
								/>
							</a>
						{/each}
					</g>
				</svg>
				<div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
					<span class="text-sm leading-none font-semibold tabular-nums">
						{exposure.services.toLocaleString()}
					</span>
				</div>
			</div>
		{/if}
		<ul class="flex min-w-0 flex-1 flex-col gap-1">
			{#each slices as b (b.key)}
				<li>
					<a
						href={link(b.query)}
						class="flex items-center gap-2 text-xs hover:text-foreground"
						onmouseenter={() => (hovered = b.key)}
						onmouseleave={() => (hovered = null)}
					>
						<span
							class="size-2 shrink-0 rounded-full"
							style="background:{SERVICE_CLASS_FILL[b.key] ?? 'var(--chart-5)'}"
						></span>
						<span class="min-w-0 flex-1 truncate text-muted-foreground">
							{SERVICE_CLASS_LABELS[b.key] ?? b.label}
						</span>
						<span class="font-medium tabular-nums">{b.count.toLocaleString()}</span>
						<span class="w-8 text-right text-2xs text-muted-foreground tabular-nums">
							{exposure.services ? Math.round((b.count / exposure.services) * 100) : 0}%
						</span>
					</a>
				</li>
			{/each}
		</ul>
	</div>
	{#if top.length}
		<RankedBars rows={top} dense />
	{/if}
	{#snippet footer()}
		{#if exposure.sensitive > 0}
			<a href={link('is:sensitive')} class="font-medium text-foreground">
				{exposure.sensitive.toLocaleString()} sensitive{#if !scanId}
					on {exposure.sensitive_targets}
					{exposure.sensitive_targets === 1 ? 'target' : 'targets'}{/if}
			</a>
		{:else}
			<span>No sensitive service</span>
		{/if}
	{/snippet}
</Cell>
