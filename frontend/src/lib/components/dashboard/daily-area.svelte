<script lang="ts" module>
	export interface DailyLevel {
		date: string;
		total: number;
		added: number;
		retired: number;
		runs: number;
	}
</script>

<script lang="ts">
	import { scalePoint } from 'd3-scale';
	import { curveStepAfter } from 'd3-shape';
	import { Area, AreaChart, LinearGradient } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';
	import type { TooltipPayload } from '$lib/components/ui/chart/chart-utils';

	interface Props {
		data: DailyLevel[];
		label: string;
		height?: number;
		class?: string;
	}

	let { data, label, height = 190, class: className = '' }: Props = $props();

	let config = $derived({ total: { label, color: 'var(--series)' } } satisfies Chart.ChartConfig);
	let series = $derived([{ key: 'total', label, color: 'var(--series)' }]);
	const stops = [
		'color-mix(in oklab, var(--series) 28%, transparent)',
		'color-mix(in oklab, var(--series) 3%, transparent)'
	];
	let every = $derived(data.length <= 7 ? 1 : data.length <= 14 ? 2 : 5);
	let ticks = $derived(
		data.map((d) => d.date).filter((_, i) => (data.length - 1 - i) % every === 0)
	);
	let runDays = $derived(data.filter((d) => d.runs > 0));
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
	const fmtValue = (v: unknown) => (typeof v === 'number' ? v.toLocaleString() : String(v ?? ''));
	const rowOf = (payload: TooltipPayload[]): DailyLevel | null => {
		const first = payload[0]?.payload;
		return first && typeof first === 'object' && 'date' in first ? (first as DailyLevel) : null;
	};
</script>

<Chart.Container
	{config}
	class="aspect-auto w-full [&_.lc-highlight-rect]:fill-muted/40 {className}"
	style="height:{height}px"
>
	<AreaChart
		{data}
		x="date"
		{series}
		xScale={scalePoint()}
		yDomain={[0, null]}
		yPadding={[0, 8]}
		axis={true}
		grid={{ x: false, y: true }}
		legend={false}
		padding={{ top: 6, left: 34, right: 8, bottom: 22 }}
		props={{
			area: { curve: curveStepAfter, fillOpacity: 1, line: { class: 'stroke-[1.5px]' } },
			xAxis: { ticks, tickLength: 0, format: fmtDay },
			yAxis: { ticks: 3, tickLength: 0, format: 'metric' },
			grid: { class: 'stroke-border/60' },
			highlight: { points: { r: 4 }, lines: { class: 'stroke-border' } }
		}}
	>
		{#snippet marks({ visibleSeries, getAreaProps })}
			{#each visibleSeries as s, i (s.key)}
				<LinearGradient {stops} vertical>
					{#snippet children({ gradient })}
						<Area {...getAreaProps(s, i)} fill={gradient} />
					{/snippet}
				</LinearGradient>
			{/each}
		{/snippet}
		{#snippet aboveMarks({ context })}
			{#each runDays as d (d.date)}
				{@const x = context.xScale(d.date)}
				{#if x !== undefined}
					<circle
						cx={x}
						cy={context.yScale(d.total)}
						r="3"
						class="fill-series stroke-card stroke-[1.5px]"
					/>
				{/if}
			{/each}
		{/snippet}
		{#snippet tooltip()}
			<Chart.Tooltip class="min-w-[11rem]" labelFormatter={fmtFullDay}>
				{#snippet formatter({ value, name, item })}
					<span class="flex flex-1 items-center justify-between gap-4">
						<span class="flex items-center gap-1.5 text-muted-foreground">
							<span class="size-2.5 rounded-[2px]" style="background:{item.color}"></span>
							{name}
						</span>
						<span class="font-mono font-medium tabular-nums">{fmtValue(value)}</span>
					</span>
				{/snippet}
				{#snippet footer({ payload })}
					{@const row = rowOf(payload)}
					{#if row}
						<div class="mt-1 grid gap-1 border-t pt-1.5 text-xs">
							{#if row.runs}
								<span class="flex justify-between gap-4">
									<span class="text-muted-foreground">Added</span>
									<span class="font-mono tabular-nums">+{row.added.toLocaleString()}</span>
								</span>
								<span class="flex justify-between gap-4">
									<span class="text-muted-foreground">Retired</span>
									<span class="font-mono tabular-nums">−{row.retired.toLocaleString()}</span>
								</span>
								<span class="flex justify-between gap-4">
									<span class="text-muted-foreground">Runs</span>
									<span class="font-mono tabular-nums">{row.runs}</span>
								</span>
							{:else}
								<span class="text-muted-foreground">No run</span>
							{/if}
						</div>
					{/if}
				{/snippet}
			</Chart.Tooltip>
		{/snippet}
	</AreaChart>
</Chart.Container>
