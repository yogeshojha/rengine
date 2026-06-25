<script lang="ts">
	import { scaleUtc } from 'd3-scale';
	import { curveNatural } from 'd3-shape';
	import { cubicInOut } from 'svelte/easing';
	import { Area, AreaChart, ChartClipPath } from 'layerchart';
	import Activity from '@lucide/svelte/icons/activity';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import * as Chart from '$lib/components/ui/chart';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import type { ScanDailyCount, ScanStatus } from '$lib/types/scan';

	interface Props {
		daily: ScanDailyCount[];
	}
	let { daily }: Props = $props();

	type StatusKey = ScanStatus;

	const SERIES_COLORS: Record<StatusKey, string> = {
		completed: 'var(--chart-1)',
		running: 'var(--chart-2)',
		pending: 'var(--chart-3)',
		cancelled: 'var(--muted-foreground)',
		failed: 'var(--destructive)'
	};

	const SERIES: { key: StatusKey; label: string; color: string }[] = (
		['completed', 'running', 'pending', 'cancelled', 'failed'] as StatusKey[]
	).map((key) => ({ key, label: SCAN_STATUS_LABEL[key], color: SERIES_COLORS[key] }));

	const chartConfig = Object.fromEntries(
		SERIES.map((s) => [s.key, { label: s.label, color: s.color }])
	) satisfies Chart.ChartConfig;

	const RANGES = [
		{ value: '30d', label: 'Last 30 days', days: 30 },
		{ value: '14d', label: 'Last 14 days', days: 14 },
		{ value: '7d', label: 'Last 7 days', days: 7 }
	] as const;

	let timeRange = $state('30d');
	let rangeDays = $derived(RANGES.find((r) => r.value === timeRange)?.days ?? 30);
	let rangeLabel = $derived(RANGES.find((r) => r.value === timeRange)?.label ?? 'Last 30 days');

	let recent = $derived(daily.slice(-rangeDays));
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

	// Only series with data in the window — avoids stacking empty statuses (baseline
	// artifact + padding the tooltip with "Cancelled 0" rows).
	let chartSeries = $derived(
		SERIES.filter((s) => recent.some((d) => d[s.key] > 0)).map((s) => ({
			key: s.key,
			label: s.label,
			color: s.color
		}))
	);
	let hasActivity = $derived(chartSeries.length > 0);
	let runs = $derived(recent.reduce((sum, d) => sum + d.count, 0));

	function fmtDay(v: Date): string {
		return v.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}
</script>

<Card.Root class="gap-0 py-0">
	<Card.Header
		class="flex flex-row items-center justify-between gap-2 space-y-0 border-b px-4 py-3 sm:px-6"
	>
		<div class="flex min-w-0 items-center gap-2">
			<Activity class="h-4 w-4 shrink-0 text-muted-foreground" />
			<Card.Title class="text-sm font-medium">Scan activity</Card.Title>
			{#if runs > 0}
				<span class="truncate text-xs tabular-nums text-muted-foreground">
					· {runs}
					{runs === 1 ? 'scan' : 'scans'}
				</span>
			{/if}
		</div>
		<Select.Root type="single" bind:value={timeRange}>
			<Select.Trigger size="sm" class="w-[132px] rounded-lg text-xs" aria-label="Select time range">
				{rangeLabel}
			</Select.Trigger>
			<Select.Content class="rounded-xl">
				{#each RANGES as r (r.value)}
					<Select.Item value={r.value} label={r.label} class="rounded-lg text-xs">
						{r.label}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</Card.Header>
	<Card.Content class="px-2 py-4 sm:px-6">
		{#if hasActivity}
			<Chart.Container config={chartConfig} class="aspect-auto h-[250px] w-full">
				<AreaChart
					legend
					{data}
					x="date"
					xScale={scaleUtc()}
					series={chartSeries}
					seriesLayout="stack"
					props={{
						xAxis: { ticks: rangeDays <= 7 ? 7 : 6, format: fmtDay },
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
			<div class="flex h-[250px] items-center justify-center text-sm text-muted-foreground">
				No scans in the {rangeLabel.toLowerCase()}.
			</div>
		{/if}
	</Card.Content>
</Card.Root>
