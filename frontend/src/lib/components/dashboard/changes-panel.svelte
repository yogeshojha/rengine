<script lang="ts" module>
	import type { SurfaceDimension as Dimension } from '$lib/config/surface';
	export type ChartMetric = Dimension | 'runs';
</script>

<script lang="ts">
	import { scaleUtc } from 'd3-scale';
	import { curveMonotoneX } from 'd3-shape';
	import { Area, AreaChart, ChartClipPath, LinearGradient } from 'layerchart';
	import { cubicInOut } from 'svelte/easing';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChartSpline from '@lucide/svelte/icons/chart-spline';
	import * as Card from '$lib/components/ui/card';
	import * as Chart from '$lib/components/ui/chart';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { getTargetTypeIcon } from '$lib/config/icons';
	import { SURFACE, SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
	import { formatTargetType, type TargetType } from '$lib/types/target';
	import { relativeTime } from '$lib/utilities/dates';
	import { isLiveStatus, SCAN_STATUS_DOT, SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import {
		windowText,
		type DashboardChangeRow,
		type DashboardOverview,
		type DashboardWindow
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		metric: ChartMetric;
		onMetric: (m: ChartMetric) => void;
	}

	let { overview, window, metric, onMetric }: Props = $props();

	const SHOWN = 8;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const METRICS: { key: ChartMetric; label: string; unit: string }[] = [
		...[
			SurfaceDimension.WEB_ASSETS,
			SurfaceDimension.SERVICES,
			SurfaceDimension.VULNERABILITIES
		].map((k) => ({ key: k, label: SURFACE[k].label, unit: `new ${SURFACE[k].nounPlural}` })),
		{ key: 'runs', label: 'Runs', unit: 'runs' }
	];
	const chartConfig = {
		value: { label: 'Value', color: 'var(--chart-1)' }
	} satisfies Chart.ChartConfig;
	const stops = [
		'color-mix(in oklab, var(--chart-1) 85%, transparent)',
		'color-mix(in oklab, var(--chart-1) 20%, transparent)'
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
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let expanded = $state(false);
	let days = $derived(window === '30d' ? 30 : 7);
	let active = $derived(METRICS.find((m) => m.key === metric) ?? METRICS[0]);
	let series = $derived([{ key: 'value', label: active.label, color: 'var(--chart-1)' }]);
	let recent = $derived(overview.daily.slice(-days));
	let chartData = $derived(
		recent.map((d) => ({
			date: new Date(`${d.date}T00:00:00Z`),
			value: metric === 'runs' ? d.runs : (d.new[metric] ?? 0),
			failed: d.failed
		}))
	);
	let total = $derived(chartData.reduce((n, d) => n + d.value, 0));
	let failedTotal = $derived(recent.reduce((n, d) => n + d.failed, 0));
	let failureDays = $derived(metric === 'runs' ? chartData.filter((d) => d.failed > 0) : []);
	let xTicks = $derived.by(() => {
		const dates = chartData.map((d) => d.date);
		if (dates.length < 4) return dates;
		const inner = dates.slice(1, -1);
		const want = Math.min(days <= 7 ? 4 : 5, inner.length);
		const step = (inner.length - 1) / (want - 1);
		return Array.from({ length: want }, (_, i) => inner[Math.round(i * step)]);
	});
	let changes = $derived(overview.changes);
	let rows = $derived(expanded ? changes : changes.slice(0, SHOWN));
	let hidden = $derived(changes.length - rows.length);

	interface Chip {
		key: string;
		text: string;
		kind: 'new' | 'gone' | 'first';
		href?: string;
		hint: string;
	}
	function chipsFor(r: DashboardChangeRow): Chip[] {
		const out: Chip[] = [];
		for (const spec of SURFACE_ORDER) {
			const fresh = r.new[spec.key];
			if (!fresh) continue;
			const scanId = r.new_scan[spec.key];
			out.push({
				key: `new:${spec.key}`,
				text: `${fresh.toLocaleString()} new ${fresh === 1 ? spec.noun : spec.nounPlural}`,
				kind: 'new',
				href: scanId
					? ROUTES.scanTab(scanId, spec.tab, { [spec.queryParam]: 'is:new' })
					: undefined,
				hint: scanId ? '' : `First seen across ${plural(r.runs, 'run', 'runs')} in the window`
			});
		}
		if (r.gone_web_assets > 0)
			out.push({
				key: 'gone',
				text: `${r.gone_web_assets.toLocaleString()} ${r.gone_web_assets === 1 ? WEB.noun : WEB.nounPlural} not seen`,
				kind: 'gone',
				hint: 'Present in the previous completed run, absent from the latest'
			});
		const first = r.first.map((key) => SURFACE[key as SurfaceDimension]).filter(Boolean);
		if (first.length)
			out.push({
				key: 'first',
				text: `baseline for ${first.map((spec) => spec.nounPlural).join(', ')}`,
				kind: 'first',
				href: ROUTES.scanTab(r.last_scan_id, first[0].tab),
				hint: 'The first run to cover these, so nothing counts as new yet'
			});
		return out;
	}
	function detailFor(r: DashboardChangeRow): string {
		const parts: string[] = [];
		if (isLiveStatus(r.last_status))
			parts.push(liveScans.runFor(r.last_scan_id)?.stage?.title ?? 'Running');
		else {
			if (r.last_status !== 'completed') parts.push(SCAN_STATUS_LABEL[r.last_status]);
			parts.push(relativeTime(r.last_at));
		}
		if (r.runs > 1) parts.push(plural(r.runs, 'run', 'runs'));
		return parts.join(' · ');
	}
	const CHIP: Record<Chip['kind'], string> = {
		new: 'border-success/40 text-success',
		gone: 'border-dashed text-muted-foreground',
		first: 'text-muted-foreground'
	};
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="What changed">
		<span class="tabular-nums">
			{plural(overview.runs_in_window, 'run', 'runs')} in the {windowText(window)}
			{#if overview.failed_in_window > 0}
				· <span class="text-destructive">{overview.failed_in_window} failed or stopped</span>
			{/if}
		</span>
	</PanelHead>

	<div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 px-5 pt-4 pb-2">
		<p class="text-sm text-muted-foreground">
			<span class="text-lg font-semibold text-foreground tabular-nums"
				>{total.toLocaleString()}</span
			>
			{active.unit} in the last {days} days
			{#if metric === 'runs' && failedTotal > 0}
				· <span class="text-destructive">{failedTotal} failed or stopped</span>
			{/if}
		</p>
		<ToggleGroup.Root
			type="single"
			variant="outline"
			size="sm"
			value={metric}
			onValueChange={(v) => v && onMetric(v as ChartMetric)}
			aria-label="Chart metric"
		>
			{#each METRICS as m (m.key)}
				<ToggleGroup.Item value={m.key} class="px-2.5">{m.label}</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
	</div>

	{#if total === 0}
		<EmptyState
			compact
			icon={ChartSpline}
			title={metric === 'runs'
				? `No runs in the last ${days} days`
				: `No new ${active.label.toLowerCase()} in the last ${days} days`}
			class="mx-5 mb-4 h-[160px] justify-center border-0 bg-transparent"
		/>
	{:else}
		{#key `${metric}:${days}`}
			<Chart.Container
				config={chartConfig}
				class="aspect-auto h-[160px] w-full [&_.lc-highlight-line]:stroke-border [&_.lc-highlight-line]:stroke-1 [&_.lc-highlight-point]:stroke-background [&_.lc-highlight-point]:stroke-2"
			>
				<AreaChart
					data={chartData}
					x="date"
					xScale={scaleUtc()}
					yDomain={[0, null]}
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
									cy={context.yScale(d.value)}
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
								{#if metric === 'runs' && (day?.failed ?? 0) > 0}
									<div
										class="mt-0.5 flex items-center justify-between gap-4 border-t border-border/50 pt-1.5"
									>
										<span class="flex items-center gap-1.5 text-destructive">
											<span class="size-2.5 rounded-[2px] bg-destructive"></span>
											Failed or stopped
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

	{#if changes.length}
		<div class="border-t px-5 pt-2 pb-3">
			<ul class="flex flex-col divide-y divide-border/60">
				{#each rows as r (r.target_id)}
					{@const chips = chipsFor(r)}
					{@const Icon = getTargetTypeIcon(r.target_type as TargetType, true)}
					{@const live = isLiveStatus(r.last_status)}
					<li class="flex flex-wrap items-start gap-x-4 gap-y-1.5 py-2.5">
						<span class="flex min-w-0 items-center gap-2.5 sm:w-64">
							<Hint text={formatTargetType(r.target_type as TargetType)}>
								{#snippet child(props)}
									<span
										{...props}
										class="flex size-6 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground"
									>
										<Icon class="size-3.5" />
									</span>
								{/snippet}
							</Hint>
							<span class="flex min-w-0 flex-col leading-4">
								<a
									href={ROUTES.target(r.target_id)}
									class="truncate font-mono text-xs font-semibold hover:underline"
								>
									{r.target_value}
								</a>
								<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
									<span class="flex h-4 shrink-0 items-center">
										{#if live}
											<Spinner class="size-2.5 text-info" />
										{:else}
											<span
												class="size-2 rounded-full border-2 {SCAN_STATUS_DOT[r.last_status]}"
												aria-hidden="true"
											></span>
										{/if}
									</span>
									<span class="truncate">{detailFor(r)}</span>
								</span>
							</span>
						</span>
						<span class="flex min-w-0 flex-1 flex-wrap items-center gap-1.5 sm:pt-0.5">
							{#if chips.length}
								{#each chips as c (c.key)}
									<Hint text={c.hint}>
										{#snippet child(props)}
											{#if c.href}
												<a
													{...props}
													href={c.href}
													class="inline-flex h-5 items-center gap-0.5 rounded-md border px-[7px] text-xs tabular-nums transition-colors hover:bg-accent/60 {CHIP[
														c.kind
													]}"
												>
													{#if c.kind === 'new'}<ArrowUpRight class="size-3" />{/if}
													{c.text}
												</a>
											{:else}
												<span
													{...props}
													class="inline-flex h-5 items-center gap-0.5 rounded-md border px-[7px] text-xs tabular-nums {CHIP[
														c.kind
													]}"
												>
													{#if c.kind === 'new'}<ArrowUpRight
															class="size-3"
														/>{:else if c.kind === 'gone'}<ArrowDownRight class="size-3" />{/if}
													{c.text}
												</span>
											{/if}
										{/snippet}
									</Hint>
								{/each}
							{:else}
								<span class="text-xs leading-5 text-muted-foreground">No change</span>
							{/if}
						</span>
					</li>
				{/each}
			</ul>
			{#if hidden > 0}
				<Button
					variant="link"
					size="sm"
					class="mt-2 h-auto gap-1 px-0 text-xs"
					onclick={() => (expanded = true)}
				>
					Show {hidden} more {hidden === 1 ? 'target' : 'targets'}
					<ChevronDown class="size-3.5" />
				</Button>
			{/if}
		</div>
	{/if}
</Card.Root>
