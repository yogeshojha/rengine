<script lang="ts">
	import { useScopedRoutes } from './scope-links';
	import Cell from './cell.svelte';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import {
		SEVERITY_FILL,
		SEVERITY_LABELS,
		SEVERITY_ORDER,
		Severity
	} from '$lib/config/vulnerabilities';
	import { cappedCount } from '$lib/utilities/strings';
	import {
		bucketsSince,
		windowDays,
		type DashboardOverview,
		type DashboardWindow,
		type DashboardWindowCounts
	} from '$lib/types/dashboard';

	const routes = useScopedRoutes();

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		counts: DashboardWindowCounts | null;
		loading?: boolean;
		class?: string;
	}

	let { overview, window, counts, loading = false, class: className = '' }: Props = $props();

	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];
	const SEVERITIES = SEVERITY_ORDER.filter((s) => s !== Severity.UNKNOWN);

	let days = $derived(windowDays(window));
	let recent = $derived(bucketsSince(overview.daily, overview.since));
	let found = $derived(counts?.new.find((c) => c.key === SurfaceDimension.VULNERABILITIES) ?? null);
	let data = $derived<DailyPoint[]>(
		recent.map((d) => ({
			date: d.date,
			...Object.fromEntries(SEVERITIES.map((s) => [s, d.findings[s] ?? 0]))
		}))
	);
	let totals = $derived(
		SEVERITIES.map((s) => ({
			key: s,
			label: SEVERITY_LABELS[s],
			color: SEVERITY_FILL[s],
			count: counts?.findings[s] ?? 0
		}))
	);
	let series = $derived(
		totals
			.filter((t) => t.count > 0 || recent.some((d) => (d.findings[t.key] ?? 0) > 0))
			.map((t) => ({ key: t.key, label: t.label, color: t.color }))
	);
	let urgent = $derived(
		totals
			.filter((t) => t.key === Severity.CRITICAL || t.key === Severity.HIGH)
			.reduce((n, t) => n + t.count, 0)
	);
</script>

<Cell
	id="findings-trend"
	description="First reported per day"
	href={found ? routes.rows(VULN.key, found.query) : undefined}
	hrefLabel={found?.query}
	loading={loading && !counts}
	class={className}
>
	{#key window}
		<DailyBars {data} {series} height={170} />
	{/key}
	<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
		{#each totals as t (t.key)}
			<span class="flex items-center gap-1.5">
				<span class="size-2.5 rounded-[2px]" style="background:{t.color}"></span>
				{t.label}
				<span class="font-medium text-foreground tabular-nums">{t.count.toLocaleString()}</span>
			</span>
		{/each}
	</div>
	{#snippet footer()}
		<span>
			{#if found}
				{cappedCount(found.count, found.capped)} first reported in {days} days ·
				{urgent.toLocaleString()} critical or high
			{/if}
		</span>
	{/snippet}
</Cell>
