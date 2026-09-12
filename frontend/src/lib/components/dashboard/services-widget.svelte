<script lang="ts">
	import { arc, pie } from 'd3-shape';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Hint from '$lib/components/hint.svelte';
	import Widget from './widget.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import ServiceIcon from '$lib/components/scans/results/services/service-icon.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { SERVICE_CLASS_FILL, SERVICE_CLASS_LABELS } from '$lib/config/service-classes';
	import type { DashboardExposure } from '$lib/types/dashboard';

	interface Props {
		exposure: DashboardExposure;
		class?: string;
	}

	let { exposure, class: className = '' }: Props = $props();

	const SIZE = 132;
	const RING = 16;
	const SPEC = SURFACE[SurfaceDimension.SERVICES];
	const TOP = 5;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	const link = (q: string) => ROUTES.surface(SPEC.tab, { [SPEC.queryParam]: q });

	let slices = $derived(exposure.bands.filter((b) => b.count > 0));
	let arcs = $derived.by(() => {
		const layout = pie<{ count: number }>()
			.value((d) => d.count)
			.sort(null)
			.padAngle(0.02);
		const shape = arc<{ startAngle: number; endAngle: number; padAngle: number }>()
			.innerRadius(SIZE / 2 - RING)
			.outerRadius(SIZE / 2)
			.cornerRadius(2);
		return layout(slices).map((a, i) => ({
			d: shape(a) ?? '',
			band: slices[i],
			share: exposure.services ? Math.round((slices[i].count / exposure.services) * 100) : 0
		}));
	});
	let hovered = $state<string | null>(null);

	let top = $derived<BarRow[]>(
		exposure.top.slice(0, TOP).map((t) => ({
			key: t.key,
			label: t.label,
			count: t.count,
			sub: t.sensitive ? 'sensitive' : undefined,
			href: link(t.query),
			tone: t.sensitive ? 'var(--destructive)' : 'var(--series)'
		}))
	);
</script>

<Widget
	title="Services"
	description="Service classes from the latest service scan of each target"
	href={ROUTES.surface(SPEC.tab)}
	hrefLabel="Services"
	class={className}
>
	<div class="flex flex-col gap-4 px-5 py-4">
		<div class="flex items-center gap-5">
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
					<div
						class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
					>
						{#if hovered}
							{@const a = arcs.find((x) => x.band.key === hovered)}
							<span class="text-lg leading-none font-semibold tabular-nums">{a?.share}%</span>
							<span class="mt-1 text-[11px] text-muted-foreground">{a?.band.label}</span>
						{:else}
							<span class="text-lg leading-none font-semibold tabular-nums">
								{exposure.services.toLocaleString()}
							</span>
							<span class="mt-1 text-[11px] text-muted-foreground">services</span>
						{/if}
					</div>
				</div>
			{/if}
			<ul class="flex min-w-0 flex-1 flex-col gap-1">
				{#each slices as b (b.key)}
					<li>
						<a
							href={link(b.query)}
							class="flex items-center gap-2 rounded-sm text-sm hover:text-foreground"
							onmouseenter={() => (hovered = b.key)}
							onmouseleave={() => (hovered = null)}
						>
							<span
								class="size-2.5 shrink-0 rounded-[3px]"
								style="background:{SERVICE_CLASS_FILL[b.key] ?? 'var(--chart-5)'}"
							></span>
							<span class="min-w-0 flex-1 truncate text-muted-foreground">
								{SERVICE_CLASS_LABELS[b.key] ?? b.label}
							</span>
							<span class="font-medium tabular-nums">{b.count.toLocaleString()}</span>
							<span class="w-9 text-right text-[11px] text-muted-foreground tabular-nums">
								{exposure.services ? Math.round((b.count / exposure.services) * 100) : 0}%
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>

		{#if exposure.sensitive > 0}
			<a
				href={link('is:sensitive')}
				class="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm hover:bg-destructive/10"
			>
				<ShieldAlert class="size-4 shrink-0 text-destructive" />
				<span class="min-w-0 flex-1">
					<b class="font-semibold tabular-nums">{exposure.sensitive.toLocaleString()}</b>
					sensitive {exposure.sensitive === 1 ? 'service' : 'services'} on
					{plural(exposure.sensitive_targets, 'target', 'targets')}
				</span>
			</a>
		{/if}

		{#if top.length}
			<div class="flex flex-col gap-2">
				<span class="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
					Top non-web services
				</span>
				<RankedBars rows={top} dense>
					{#snippet icon(r)}
						{@const t = exposure.top.find((x) => x.key === r.key)}
						{#if t}
							<Hint text={t.label}>
								{#snippet child(props)}
									<span {...props} class="inline-flex">
										<ServiceIcon service={t.key} serviceClass={t.service_class} class="size-4" />
									</span>
								{/snippet}
							</Hint>
						{/if}
					{/snippet}
				</RankedBars>
			</div>
		{/if}
	</div>
</Widget>
