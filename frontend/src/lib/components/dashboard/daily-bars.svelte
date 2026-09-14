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

	interface Props {
		data: DailyPoint[];
		series: DailySeries[];
		height?: number;
		diverging?: boolean;
		hollow?: string[];
		marker?: string | null;
		class?: string;
	}

	let {
		data,
		series,
		height = 150,
		diverging = false,
		hollow = [],
		marker = null,
		class: className = ''
	}: Props = $props();

	let config = $derived(
		Object.fromEntries(
			series.map((s) => [s.key, { label: s.label, color: s.color }])
		) satisfies Chart.ChartConfig
	);
	let chartSeries = $derived(
		series.map((s) => ({
			key: s.key,
			label: s.label,
			color: s.color,
			props: hollow.includes(s.key)
				? { class: 'fill-transparent stroke-series stroke-[1.5px]' }
				: undefined
		}))
	);
	let every = $derived(
		height < 100 ? Math.max(1, data.length - 1) : data.length <= 7 ? 1 : data.length <= 14 ? 2 : 5
	);
	let ticks = $derived(
		data.map((d) => d.date).filter((_, i) => (data.length - 1 - i) % every === 0)
	);
	const fmtDay = (v: string) =>
		new Date(`${v}T00:00:00Z`).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	const fmtFullDay = (v: string) =>
		new Date(`${v}T00:00:00Z`).toLocaleDateString('en-US', {
			weekday: 'short',
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	const fmtValue = (v: unknown) =>
		typeof v === 'number' ? Math.abs(v).toLocaleString() : String(v ?? '');
</script>

<Chart.Container
	{config}
	class="aspect-auto w-full [&_.lc-highlight-rect]:fill-muted/40 {className}"
	style="height:{height}px"
>
	<BarChart
		{data}
		x="date"
		series={chartSeries}
		seriesLayout={diverging ? 'stackDiverging' : 'stack'}
		bandPadding={0.5}
		stackPadding={2}
		axis={true}
		grid={{ x: false, y: true }}
		rule={diverging}
		padding={{ top: 6, left: 34, right: 8, bottom: 22 }}
		props={{
			bars: { rounded: 'top', radius: 2, strokeWidth: 0 },
			xAxis: { ticks, tickLength: 0, format: fmtDay },
			yAxis: { ticks: 3, tickLength: 0, format: 'metric' },
			grid: { class: 'stroke-border/60' },
			highlight: { area: true, bar: false }
		}}
	>
		{#snippet aboveMarks({ context })}
			{#if marker && context.xScale(marker) !== undefined}
				{@const x = context.xScale(marker) ?? 0}
				<line
					x1={x}
					x2={x}
					y1={0}
					y2={context.height}
					class="stroke-primary stroke-[1.5px]"
					stroke-dasharray="3 3"
				/>
			{/if}
		{/snippet}
		{#snippet tooltip()}
			<Chart.Tooltip class="min-w-[10rem]" labelFormatter={fmtFullDay}>
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
