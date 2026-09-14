<script lang="ts">
	import Cell from './cell.svelte';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { SEVERITY_FILL, SEVERITY_LABELS, SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import { windowDays, type DashboardOverview, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		class?: string;
	}

	let { overview, window, class: className = '' }: Props = $props();

	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];
	const SEVERITIES = SEVERITY_ORDER.filter((s) => s !== 'unknown');

	let days = $derived(windowDays(window));
	let recent = $derived(overview.daily.slice(-days));
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
			count: recent.reduce((n, d) => n + (d.findings[s] ?? 0), 0)
		}))
	);
	let series = $derived(
		totals.filter((t) => t.count > 0).map((t) => ({ key: t.key, label: t.label, color: t.color }))
	);
	let total = $derived(totals.reduce((n, t) => n + t.count, 0));
	let urgent = $derived(
		totals.filter((t) => t.key === 'critical' || t.key === 'high').reduce((n, t) => n + t.count, 0)
	);
</script>

<Cell
	id="findings-trend"
	title="Findings by severity"
	description="First reported per day"
	href={ROUTES.surface(VULN.tab, { [VULN.queryParam]: 'is:new' })}
	hrefLabel="is:new"
	class={className}
>
	{#key window}
		<DailyBars {data} {series} height={170} />
	{/key}
	<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
		{#each totals as t (t.key)}
			<a
				href={ROUTES.surface(VULN.tab, { [VULN.queryParam]: `severity:${t.key}` })}
				class="flex items-center gap-1.5 hover:text-foreground"
			>
				<span class="size-2.5 rounded-full" style="background:{t.color}"></span>
				{t.label}
				<span class="font-medium text-foreground tabular-nums">{t.count.toLocaleString()}</span>
			</a>
		{/each}
	</div>
	{#snippet footer()}
		<span>
			{total.toLocaleString()} first reported in {days} days · {urgent.toLocaleString()} critical or high
		</span>
	{/snippet}
</Cell>
