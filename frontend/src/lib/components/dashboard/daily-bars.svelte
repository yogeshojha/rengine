<script lang="ts" module>
	export interface DailySeries {
		key: string;
		label: string;
		color: string;
	}
	export interface DailyPoint {
		date: string;
		[key: string]: number | string;
	}
</script>

<script lang="ts">
	import { BarChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';
	import { formatDay } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';

	interface Props {
		data: DailyPoint[];
		series: DailySeries[];
		height?: number;
	}

	let { data, series, height = 150 }: Props = $props();

	let config = $derived(
		Object.fromEntries(
			series.map((s) => [s.key, { label: s.label, color: s.color }])
		) satisfies Chart.ChartConfig
	);
	let every = $derived(
		height < 100 ? Math.max(1, data.length - 1) : data.length <= 7 ? 1 : data.length <= 14 ? 2 : 5
	);
	let ticks = $derived(
		data.map((d) => d.date).filter((_, i) => (data.length - 1 - i) % every === 0)
	);
	const fmtValue = (v: unknown) => (typeof v === 'number' ? v.toLocaleString() : String(v ?? ''));
	let summary = $derived(
		`${series.map((s) => `${s.label} ${data.reduce((n, d) => n + (Number(d[s.key]) || 0), 0).toLocaleString()}`).join(', ')} in ${plural(data.length, 'day')}`
	);
</script>

<Chart.Container
	{config}
	role="img"
	aria-label={summary}
	class="aspect-auto w-full [&_.lc-highlight-rect]:fill-muted/40"
	style="height:{height}px"
>
	<BarChart
		{data}
		x="date"
		{series}
		seriesLayout="stack"
		bandPadding={0.5}
		stackPadding={2}
		axis={true}
		grid={{ x: false, y: true }}
		rule={false}
		padding={{ top: 6, left: 34, right: 8, bottom: 22 }}
		props={{
			bars: { rounded: 'top', radius: 2, strokeWidth: 0 },
			xAxis: { ticks, tickLength: 0, format: (v: string) => formatDay(v) },
			yAxis: { ticks: 3, tickLength: 0, format: 'metric' },
			grid: { class: 'stroke-border/60' },
			highlight: { area: true, bar: false }
		}}
	>
		{#snippet tooltip()}
			<Chart.Tooltip class="min-w-[10rem]" labelFormatter={(v: string) => formatDay(v, true)}>
				{#snippet formatter({ value, name, item })}
					<span class="flex flex-1 items-center justify-between gap-4">
						<span class="flex items-center gap-1.5 text-muted-foreground">
							<span class="size-2.5 rounded-[2px]" style="background:{item.color}"></span>
							{name}
						</span>
						<span class="font-mono font-medium tabular-nums">{fmtValue(value)}</span>
					</span>
				{/snippet}
			</Chart.Tooltip>
		{/snippet}
	</BarChart>
</Chart.Container>
