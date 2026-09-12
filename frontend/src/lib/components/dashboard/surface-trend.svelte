<script lang="ts">
	import { scaleUtc } from 'd3-scale';
	import { curveStepAfter } from 'd3-shape';
	import { Area, AreaChart, ChartClipPath, LinearGradient } from 'layerchart';
	import { cubicInOut } from 'svelte/easing';
	import * as Chart from '$lib/components/ui/chart';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import Widget from './widget.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
	import type { DashboardOverview, DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		class?: string;
	}

	let { overview, window, class: className = '' }: Props = $props();

	let dim = $state<SurfaceDimension>(SurfaceDimension.WEB_ASSETS);
	let spec = $derived(SURFACE[dim]);
	let days = $derived(window === '30d' ? 30 : 7);
	let recent = $derived(overview.daily.slice(-days));
	let data = $derived(
		recent.map((d) => ({ date: new Date(`${d.date}T00:00:00Z`), value: d.total[dim] ?? 0 }))
	);
	let current = $derived(data.at(-1)?.value ?? 0);
	let opening = $derived(data[0]?.value ?? 0);
	let delta = $derived(current - opening);
	let empty = $derived(data.every((d) => d.value === 0));

	const chartConfig = {
		value: { label: 'Value', color: 'var(--series)' }
	} satisfies Chart.ChartConfig;
	let series = $derived([{ key: 'value', label: spec.label, color: 'var(--series)' }]);
	const stops = [
		'color-mix(in oklab, var(--series) 55%, transparent)',
		'color-mix(in oklab, var(--series) 4%, transparent)'
	];
	const fmtDay = (v: Date) =>
		v.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
	const fmtFullDay = (v: Date) =>
		v.toLocaleDateString('en-US', {
			weekday: 'short',
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	let xTicks = $derived.by(() => {
		const dates = data.map((d) => d.date);
		if (dates.length < 4) return dates;
		const inner = dates.slice(1, -1);
		const want = Math.min(days <= 7 ? 4 : 5, inner.length);
		const step = (inner.length - 1) / (want - 1);
		return Array.from({ length: want }, (_, i) => inner[Math.round(i * step)]);
	});
</script>

<Widget
	title="Attack surface over time"
	href={ROUTES.surface(spec.tab)}
	hrefLabel={spec.label}
	class={className}
>
	<div class="flex flex-wrap items-end justify-between gap-3 px-5 pt-4">
		<div class="flex flex-col gap-1">
			<span class="text-3xl leading-none font-semibold tracking-tight tabular-nums">
				{current.toLocaleString()}
			</span>
			<span class="flex items-center gap-2 text-xs text-muted-foreground">
				<span>{spec.nounPlural} today</span>
				{#if delta !== 0}
					<span class="font-medium tabular-nums {delta > 0 ? 'text-success' : 'text-destructive'}">
						{delta > 0 ? '▲' : '▼'}
						{Math.abs(delta).toLocaleString()} since {fmtDay(data[0].date)}
					</span>
				{:else if data.length}
					<span>unchanged since {fmtDay(data[0].date)}</span>
				{/if}
			</span>
		</div>
		<ToggleGroup.Root
			type="single"
			size="sm"
			variant="outline"
			value={dim}
			onValueChange={(v) => v && (dim = v as SurfaceDimension)}
			aria-label="Dimension"
		>
			{#each SURFACE_ORDER as s (s.key)}
				<ToggleGroup.Item value={s.key} class="gap-1.5 px-2.5 text-xs">
					<s.icon class="size-3.5" />
					<span class="hidden xl:inline">{s.label}</span>
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
	</div>
	{#if empty}
		<p class="flex flex-1 items-center justify-center px-5 py-10 text-sm text-muted-foreground">
			No {spec.nounPlural} in this window.
		</p>
	{:else}
		{#key dim + window}
			<Chart.Container
				config={chartConfig}
				class="aspect-auto min-h-[200px] w-full flex-1 pt-2 [&_.lc-highlight-line]:stroke-border [&_.lc-highlight-line]:stroke-1 [&_.lc-highlight-point]:stroke-background [&_.lc-highlight-point]:stroke-2"
			>
				<AreaChart
					{data}
					x="date"
					xScale={scaleUtc()}
					yDomain={[0, null]}
					yPadding={[0, 10]}
					padding={{ top: 8, left: 16, right: 16, bottom: 26 }}
					axis="x"
					grid={false}
					{series}
					props={{
						area: {
							curve: curveStepAfter,
							fillOpacity: 1,
							motion: 'tween',
							line: { class: 'stroke-2' }
						},
						xAxis: { ticks: xTicks, tickLength: 0, format: fmtDay },
						highlight: { points: { r: 4 } }
					}}
				>
					{#snippet marks({ visibleSeries, getAreaProps })}
						<ChartClipPath
							initialWidth={0}
							motion={{ width: { type: 'tween', duration: 700, easing: cubicInOut } }}
						>
							{#each visibleSeries as s, i (s.key)}
								<LinearGradient {stops} vertical>
									{#snippet children({ gradient })}
										<Area {...getAreaProps(s, i)} fill={gradient} />
									{/snippet}
								</LinearGradient>
							{/each}
						</ChartClipPath>
					{/snippet}
					{#snippet tooltip()}
						<Chart.Tooltip class="min-w-[10rem]" indicator="line" labelFormatter={fmtFullDay} />
					{/snippet}
				</AreaChart>
			</Chart.Container>
		{/key}
	{/if}
</Widget>
