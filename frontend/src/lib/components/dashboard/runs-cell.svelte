<script lang="ts">
	import Cell from './cell.svelte';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		SCAN_OUTCOME_FILL,
		SCAN_OUTCOME_LABELS,
		SCAN_OUTCOME_ORDER
	} from '$lib/config/dashboard';
	import { windowDays, type DashboardOverview, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		class?: string;
	}

	let { overview, window, class: className = '' }: Props = $props();

	let days = $derived(windowDays(window));
	let recent = $derived(overview.daily.slice(-days));
	let data = $derived<DailyPoint[]>(
		recent.map((d) => ({
			date: d.date,
			...Object.fromEntries(SCAN_OUTCOME_ORDER.map((k) => [k, d.outcomes[k] ?? 0]))
		}))
	);
	let totals = $derived(
		SCAN_OUTCOME_ORDER.map((k) => ({
			key: k,
			label: SCAN_OUTCOME_LABELS[k],
			color: SCAN_OUTCOME_FILL[k],
			count: recent.reduce((n, d) => n + (d.outcomes[k] ?? 0), 0)
		}))
	);
	let series = $derived(
		totals.filter((t) => t.count > 0).map((t) => ({ key: t.key, label: t.label, color: t.color }))
	);
	let total = $derived(totals.reduce((n, t) => n + t.count, 0));
	let failed = $derived(totals.find((t) => t.key === 'failed')?.count ?? 0);
</script>

<Cell
	id="runs"
	title="Scan activity"
	description="Runs per day by outcome"
	href={ROUTES.scans}
	hrefLabel="Scans"
	class={className}
>
	{#key window}
		<DailyBars {data} {series} height={150} />
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
			{total.toLocaleString()} runs in {days} days · {failed} failed
		</span>
	{/snippet}
</Cell>
