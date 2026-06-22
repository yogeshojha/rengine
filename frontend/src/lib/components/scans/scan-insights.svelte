<script lang="ts">
	import { scaleBand } from 'd3-scale';
	import { BarChart } from 'layerchart';
	import { Activity, CircleCheck, Timer } from 'lucide-svelte';
	import * as Chart from '$lib/components/ui/chart';
	import { SCAN_STATUS_LABEL, formatSeconds } from '$lib/utilities/scan-status';
	import type { ScanStats, ScanStatus } from '$lib/types/scan';

	interface Props {
		stats: ScanStats | null;
		onFilterStatus?: (statuses: ScanStatus[]) => void;
	}

	let { stats, onFilterStatus }: Props = $props();

	const SEGMENTS: { key: ScanStatus; cls: string; dot: string }[] = [
		{ key: 'completed', cls: 'bg-foreground', dot: 'bg-foreground' },
		{ key: 'running', cls: 'bg-chart-1', dot: 'bg-chart-1' },
		{ key: 'pending', cls: 'bg-muted-foreground/40', dot: 'bg-muted-foreground/40' },
		{ key: 'failed', cls: 'bg-destructive', dot: 'bg-destructive' },
		{ key: 'cancelled', cls: 'bg-destructive/50', dot: 'bg-destructive/50' }
	];

	let total = $derived(stats?.total ?? 0);
	let active = $derived(stats ? stats.by_status.running + stats.by_status.pending : 0);
	let segments = $derived(
		stats ? SEGMENTS.map((s) => ({ ...s, count: stats.by_status[s.key] })) : []
	);
	let successPct = $derived(
		stats?.success_rate != null ? Math.round(stats.success_rate * 100) : null
	);
	let avgDuration = $derived(
		stats?.avg_duration_seconds != null ? formatSeconds(stats.avg_duration_seconds) : '—'
	);

	let activity = $derived(
		(stats?.daily ?? []).slice(-14).map((d) => ({ label: d.date.slice(5), count: d.count }))
	);
	let hasActivity = $derived(activity.some((d) => d.count > 0));

	const chartConfig = {
		count: { label: 'Scans', color: 'var(--chart-1)' }
	} satisfies Chart.ChartConfig;

	function pickStatus(s: ScanStatus) {
		onFilterStatus?.([s]);
	}
</script>

{#if stats && total > 0}
	<div class="grid gap-3 lg:grid-cols-2">
		<div class="space-y-3 rounded-lg border border-border p-3">
			<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
				<div class="space-y-0.5">
					<div class="text-lg font-semibold tabular-nums">{total}</div>
					<div class="text-xs text-muted-foreground">Total scans</div>
				</div>
				<button
					type="button"
					class="space-y-0.5 rounded-md text-left transition-colors hover:bg-muted/50 disabled:cursor-default disabled:hover:bg-transparent"
					disabled={active === 0}
					onclick={() => onFilterStatus?.(['running', 'pending'])}
				>
					<div
						class="text-lg font-semibold tabular-nums {active > 0
							? 'text-amber-600 dark:text-amber-500'
							: ''}"
					>
						{active}
					</div>
					<div class="text-xs text-muted-foreground">In progress</div>
				</button>
				<div class="space-y-0.5">
					<div class="flex items-center gap-1 text-lg font-semibold tabular-nums">
						<CircleCheck class="h-3.5 w-3.5 text-muted-foreground" />
						{successPct != null ? `${successPct}%` : '—'}
					</div>
					<div class="text-xs text-muted-foreground">Success rate</div>
				</div>
				<div class="space-y-0.5">
					<div class="flex items-center gap-1 text-lg font-semibold tabular-nums">
						<Timer class="h-3.5 w-3.5 text-muted-foreground" />
						{avgDuration}
					</div>
					<div class="text-xs text-muted-foreground">Avg duration</div>
				</div>
			</div>

			<div class="flex h-2 w-full overflow-hidden rounded-full bg-muted">
				{#each segments as seg (seg.key)}
					{#if seg.count > 0}
						<button
							type="button"
							class="{seg.cls} h-full transition-opacity hover:opacity-80"
							style="width: {(seg.count / total) * 100}%"
							title="{SCAN_STATUS_LABEL[seg.key]}: {seg.count}"
							aria-label="Filter by {SCAN_STATUS_LABEL[seg.key]} ({seg.count})"
							onclick={() => pickStatus(seg.key)}
						></button>
					{/if}
				{/each}
			</div>

			<div class="flex flex-wrap gap-x-3 gap-y-1">
				{#each segments as seg (seg.key)}
					<button
						type="button"
						class="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:cursor-default disabled:opacity-50 disabled:hover:text-muted-foreground"
						disabled={seg.count === 0}
						onclick={() => pickStatus(seg.key)}
					>
						<span class="{seg.dot} h-2 w-2 rounded-full"></span>
						{SCAN_STATUS_LABEL[seg.key]}
						<span class="tabular-nums">{seg.count}</span>
					</button>
				{/each}
			</div>
		</div>

		<div class="rounded-lg border border-border p-3">
			<div class="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
				<Activity class="h-3.5 w-3.5" />
				Activity · last 14 days
			</div>
			{#if hasActivity}
				<Chart.Container config={chartConfig} class="h-[120px] w-full">
					<BarChart
						data={activity}
						x="label"
						axis="x"
						xScale={scaleBand().padding(0.3)}
						series={[{ key: 'count', label: 'Scans', color: 'var(--chart-1)' }]}
						props={{ bars: { stroke: 'none', rounded: 'top', radius: 3 } }}
					>
						{#snippet tooltip()}
							<Chart.Tooltip hideLabel={false} indicator="line" />
						{/snippet}
					</BarChart>
				</Chart.Container>
			{:else}
				<div class="flex h-[120px] items-center justify-center text-xs text-muted-foreground">
					No scans in the last 14 days.
				</div>
			{/if}
		</div>
	</div>
{/if}
