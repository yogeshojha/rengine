<script lang="ts">
	import { scaleUtc } from 'd3-scale';
	import { curveMonotoneX } from 'd3-shape';
	import { Area, AreaChart, ChartClipPath, LinearGradient } from 'layerchart';
	import { cubicInOut } from 'svelte/easing';
	import ChartSpline from '@lucide/svelte/icons/chart-spline';
	import * as Card from '$lib/components/ui/card';
	import * as Chart from '$lib/components/ui/chart';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { ScanDailyCount, ScanStats } from '$lib/types/scan';

	interface Props {
		stats: ScanStats | null;
	}

	let { stats }: Props = $props();

	type Metric = 'scans' | 'new_subdomains';

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	const chartConfig = {
		scans: { label: 'Scans', color: 'var(--chart-1)' },
		new_subdomains: { label: `New ${WEB.nounPlural}`, color: 'var(--chart-1)' }
	} satisfies Chart.ChartConfig;

	const METRICS: { value: Metric; label: string; unit: string }[] = [
		{ value: 'scans', label: 'Scans', unit: 'scans' },
		{ value: 'new_subdomains', label: WEB.label, unit: `new ${WEB.nounPlural}` }
	];
	const RANGES = [
		{ value: '7', label: '7d', full: 'last 7 days' },
		{ value: '14', label: '14d', full: 'last 14 days' },
		{ value: '30', label: '30d', full: 'last 30 days' }
	];

	let metric = $state<Metric>('scans');
	let range = $state('30');

	let rangeDays = $derived(Number(range));
	let rangeLabel = $derived(RANGES.find((r) => r.value === range)?.full ?? 'last 30 days');
	let unit = $derived(METRICS.find((m) => m.value === metric)?.unit ?? '');

	let recent = $derived<ScanDailyCount[]>((stats?.daily ?? []).slice(-rangeDays));
	let chartData = $derived(
		recent.map((d) => ({
			date: new Date(`${d.date}T00:00:00Z`),
			scans: d.count,
			new_subdomains: d.new_subdomains,
			failed: d.failed
		}))
	);

	let total = $derived(
		recent.reduce((a, d) => a + (metric === 'scans' ? d.count : d.new_subdomains), 0)
	);
	let failedTotal = $derived(recent.reduce((a, d) => a + d.failed, 0));
	let perDay = $derived(recent.length ? total / recent.length : 0);
	let failureDays = $derived(metric === 'scans' ? chartData.filter((d) => d.failed > 0) : []);

	let series = $derived([
		{ key: metric, label: chartConfig[metric].label, color: chartConfig[metric].color }
	]);
	let xTicks = $derived.by(() => {
		const dates = chartData.map((d) => d.date);
		if (dates.length < 4) return dates;
		const inner = dates.slice(1, -1);
		const want = Math.min(rangeDays <= 7 ? 4 : 5, inner.length);
		const step = (inner.length - 1) / (want - 1);
		return Array.from({ length: want }, (_, i) => inner[Math.round(i * step)]);
	});

	const fmtDay = (v: Date) =>
		v.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
	const fmtFullDay = (v: Date) =>
		v.toLocaleDateString('en-US', {
			weekday: 'short',
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	const stops = [
		'color-mix(in oklab, var(--chart-1) 85%, transparent)',
		'color-mix(in oklab, var(--chart-1) 20%, transparent)'
	];
</script>

<Card.Root class="gap-0 py-0">
	<Card.Header
		class="flex flex-col items-start justify-between gap-4 px-6 pt-6 pb-2 sm:flex-row sm:items-center"
	>
		<div class="flex flex-col gap-1.5">
			{#if stats}
				<Card.Title class="text-3xl leading-none font-semibold tracking-tight tabular-nums">
					{total.toLocaleString()}
				</Card.Title>
				<Card.Description class="flex flex-wrap items-center gap-x-2 gap-y-1">
					<span>{unit} in the {rangeLabel}</span>
					{#if metric === 'scans' && failedTotal > 0}
						<span aria-hidden="true">·</span>
						<span class="flex items-center gap-1.5 text-destructive">
							<span class="size-1.5 rounded-full bg-destructive"></span>
							{failedTotal} failed
						</span>
					{:else if metric === 'new_subdomains' && total > 0}
						<span aria-hidden="true">·</span>
						<span>{perDay < 10 ? perDay.toFixed(1) : Math.round(perDay)} per day</span>
					{/if}
				</Card.Description>
			{:else}
				<Skeleton class="h-8 w-24" />
				<Skeleton class="h-4 w-44" />
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-2">
			<ToggleGroup.Root
				type="single"
				value={metric}
				onValueChange={(v) => v && (metric = v as Metric)}
				variant="outline"
			>
				{#each METRICS as m (m.value)}
					<ToggleGroup.Item value={m.value} class="px-3">{m.label}</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
			<ToggleGroup.Root
				type="single"
				value={range}
				onValueChange={(v) => v && (range = v)}
				variant="outline"
			>
				{#each RANGES as r (r.value)}
					<ToggleGroup.Item value={r.value} class="px-3" aria-label={r.full}>
						{r.label}
					</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
		</div>
	</Card.Header>
	<Card.Content class="px-0 pt-2 pb-4">
		{#if !stats}
			<Skeleton class="h-[180px] w-full" />
		{:else if total === 0}
			<EmptyState
				compact
				icon={ChartSpline}
				title={metric === 'scans'
					? 'No scans in this window'
					: `No new ${WEB.nounPlural} in this window`}
				description={metric === 'scans'
					? `Nothing has run in the ${rangeLabel}. Launch a scan to start building history.`
					: `No first-time ${WEB.nounPlural} were discovered in the ${rangeLabel}.`}
				class="h-[180px] justify-center border-0 bg-transparent"
			/>
		{:else}
			{#key `${metric}:${range}`}
				<Chart.Container
					config={chartConfig}
					class="aspect-auto h-[180px] w-full [&_.lc-highlight-line]:stroke-border [&_.lc-highlight-line]:stroke-1 [&_.lc-highlight-point]:stroke-background [&_.lc-highlight-point]:stroke-2"
				>
					<AreaChart
						data={chartData}
						x="date"
						xScale={scaleUtc()}
						yPadding={[0, 8]}
						padding={{ top: 8, left: 16, right: 16, bottom: 26 }}
						axis="x"
						grid={false}
						{series}
						props={{
							area: {
								curve: curveMonotoneX,
								fillOpacity: 1,
								motion: 'tween',
								line: { class: 'stroke-2' }
							},
							xAxis: { ticks: xTicks, tickLength: 0, format: fmtDay },
							highlight: { points: { r: 4 } }
						}}
					>
						{#snippet marks({ visibleSeries, getAreaProps, context })}
							<ChartClipPath
								initialWidth={0}
								motion={{ width: { type: 'tween', duration: 900, easing: cubicInOut } }}
							>
								{#each visibleSeries as s, i (s.key)}
									<LinearGradient {stops} vertical>
										{#snippet children({ gradient })}
											<Area {...getAreaProps(s, i)} fill={gradient} />
										{/snippet}
									</LinearGradient>
								{/each}
								{#each failureDays as d (d.date.valueOf())}
									<circle
										cx={context.xScale(d.date)}
										cy={context.yScale(d.scans)}
										r="3.5"
										class="fill-destructive stroke-background stroke-2"
									/>
								{/each}
							</ChartClipPath>
						{/snippet}
						{#snippet tooltip()}
							<Chart.Tooltip class="min-w-[11rem]" indicator="line" labelFormatter={fmtFullDay}>
								{#snippet footer({ payload })}
									{@const day = payload[0]?.payload as { failed?: number } | undefined}
									{#if metric === 'scans' && (day?.failed ?? 0) > 0}
										<div
											class="mt-0.5 flex items-center justify-between gap-4 border-t border-border/50 pt-1.5"
										>
											<span class="flex items-center gap-1.5 text-destructive">
												<span class="size-2.5 rounded-[2px] bg-destructive"></span>
												Failed
											</span>
											<span class="font-mono font-medium text-destructive tabular-nums">
												{day?.failed}
											</span>
										</div>
									{/if}
								{/snippet}
							</Chart.Tooltip>
						{/snippet}
					</AreaChart>
				</Chart.Container>
			{/key}
		{/if}
	</Card.Content>
</Card.Root>
