<script lang="ts">
	import Cell from './cell.svelte';
	import { useScopedRoutes } from './scope-links';
	import { isScoped } from '$lib/utilities/surface-scope';
	import { plural } from '$lib/utilities/strings';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		SCAN_OUTCOME_FILL,
		SCAN_OUTCOME_LABELS,
		SCAN_OUTCOME_ORDER
	} from '$lib/config/dashboard';
	import {
		bucketsSince,
		windowDays,
		type DashboardOverview,
		type DashboardWindow
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		class?: string;
	}

	let { overview, window, class: className = '' }: Props = $props();

	const routes = useScopedRoutes();
	let scoped = $derived(isScoped(routes.scope));

	let days = $derived(windowDays(window));
	let recent = $derived(bucketsSince(overview.daily, overview.since));
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
			count: overview.outcomes_in_window[k] ?? 0
		}))
	);
	let series = $derived(
		totals
			.filter((t) => t.count > 0 || recent.some((d) => (d.outcomes[t.key] ?? 0) > 0))
			.map((t) => ({ key: t.key, label: t.label, color: t.color }))
	);
	let failed = $derived(overview.failed_in_window);
	let failedHref = $derived(
		ROUTES.scansWhere({
			status: 'failed',
			range: window,
			target: scoped ? overview.targets.map((t) => t.id) : []
		})
	);
</script>

<Cell
	id="runs"
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
			{plural(overview.runs_in_window, 'run')} in {days} days ·
			<a href={failedHref} class="hover:text-primary">
				{failed.toLocaleString()} failed
			</a>
		</span>
	{/snippet}
</Cell>
