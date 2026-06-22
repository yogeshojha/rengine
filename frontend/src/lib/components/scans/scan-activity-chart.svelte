<script lang="ts">
	import { scaleUtc } from 'd3-scale';
	import { curveNatural } from 'd3-shape';
	import { cubicInOut } from 'svelte/easing';
	import { Area, AreaChart, ChartClipPath } from 'layerchart';
	import { Activity } from 'lucide-svelte';
	import * as Chart from '$lib/components/ui/chart';
	import type { ScanDailyCount } from '$lib/types/scan';

	interface Props {
		daily: ScanDailyCount[];
	}
	let { daily }: Props = $props();

	type StatusKey = 'completed' | 'running' | 'pending' | 'cancelled' | 'failed';

	const SERIES: { key: StatusKey; label: string; color: string }[] = [
		{ key: 'completed', label: 'Completed', color: 'var(--chart-1)' },
		{ key: 'running', label: 'Running', color: 'var(--chart-2)' },
		{ key: 'pending', label: 'Queued', color: 'var(--chart-3)' },
		{ key: 'cancelled', label: 'Cancelled', color: 'var(--muted-foreground)' },
		{ key: 'failed', label: 'Failed', color: 'var(--destructive)' }
	];

	const chartConfig = Object.fromEntries(
		SERIES.map((s) => [s.key, { label: s.label, color: s.color }])
	) satisfies Chart.ChartConfig;

	let recent = $derived(daily.slice(-30));
	let data = $derived(
		recent.map((d) => ({
			date: new Date(d.date),
			completed: d.completed,
			running: d.running,
			pending: d.pending,
			cancelled: d.cancelled,
			failed: d.failed
		}))
	);

	// Only series with data in the window — avoids stacking empty statuses (which both
	// draw a baseline artifact and pad the tooltip with "Cancelled 0" rows).
	let chartSeries = $derived(
		SERIES.filter((s) => recent.some((d) => d[s.key] > 0)).map((s) => ({
			key: s.key,
			label: s.label,
			color: s.color
		}))
	);
	let hasActivity = $derived(chartSeries.length > 0);

	let totals = $derived.by(() => {
		let runs = 0;
		let completed = 0;
		let finished = 0;
		for (const d of recent) {
			runs += d.count;
			completed += d.completed;
			finished += d.completed + d.failed + d.cancelled;
		}
		return { runs, success: finished ? Math.round((completed / finished) * 100) : null };
	});

	function fmtDay(v: Date): string {
		return v.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}
</script>

<div class="rounded-lg border border-border p-3">
	<div class="mb-2 flex items-center justify-between gap-2">
		<div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
			<Activity class="h-3.5 w-3.5" />
			Scan activity · last 30 days
		</div>
		{#if totals.runs > 0}
			<div class="text-xs tabular-nums text-muted-foreground">
				{totals.runs} runs{totals.success != null ? ` · ${totals.success}% success` : ''}
			</div>
		{/if}
	</div>
	{#if hasActivity}
		<Chart.Container config={chartConfig} class="-ml-2 h-[160px] w-full">
			<AreaChart
				legend
				{data}
				x="date"
				xScale={scaleUtc()}
				series={chartSeries}
				seriesLayout="stack"
				props={{
					xAxis: { ticks: 5, format: fmtDay },
					yAxis: { format: () => '' }
				}}
			>
				{#snippet marks({ visibleSeries, getAreaProps })}
					<defs>
						{#each visibleSeries as s (s.key)}
							<linearGradient id="scanfill-{s.key}" x1="0" y1="0" x2="0" y2="1">
								<stop offset="5%" stop-color="var(--color-{s.key})" stop-opacity={0.8} />
								<stop offset="95%" stop-color="var(--color-{s.key})" stop-opacity={0.1} />
							</linearGradient>
						{/each}
					</defs>
					<ChartClipPath
						initialWidth={0}
						motion={{ width: { type: 'tween', duration: 800, easing: cubicInOut } }}
					>
						{#each visibleSeries as s, i (s.key)}
							<Area
								{...getAreaProps(s, i)}
								curve={curveNatural}
								fillOpacity={0.4}
								line={{ class: 'stroke-1' }}
								motion="tween"
								fill="url(#scanfill-{s.key})"
							/>
						{/each}
					</ChartClipPath>
				{/snippet}
				{#snippet tooltip()}
					<Chart.Tooltip labelFormatter={fmtDay} indicator="line" />
				{/snippet}
			</AreaChart>
		</Chart.Container>
	{:else}
		<div class="flex h-[160px] items-center justify-center text-xs text-muted-foreground">
			No scans in the last 30 days.
		</div>
	{/if}
</div>
