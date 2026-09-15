<script lang="ts">
	import Cell from './cell.svelte';
	import DailyArea, { type DailyLevel } from './daily-area.svelte';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
	import { windowDays, type DashboardOverview, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		class?: string;
	}

	let { overview, window, class: className = '' }: Props = $props();

	let dim = $state<string>(SurfaceDimension.WEB_ASSETS);
	let spec = $derived(SURFACE[dim as SurfaceDimension]);
	let days = $derived(windowDays(window));
	let recent = $derived(overview.daily.slice(-days));
	let data = $derived<DailyLevel[]>(
		recent.map((d) => ({
			date: d.date,
			total: d.total[dim] ?? 0,
			added: d.new[dim] ?? 0,
			retired: d.retired[dim] ?? 0,
			runs: d.runs
		}))
	);
	let added = $derived(recent.reduce((n, d) => n + (d.new[dim] ?? 0), 0));
	let retired = $derived(recent.reduce((n, d) => n + (d.retired[dim] ?? 0), 0));
	let hasRetired = $derived(retired > 0);
	let totals = $derived(
		SURFACE_ORDER.map((spec) => ({
			key: spec.key,
			label: spec.label,
			added: recent.reduce((n, d) => n + (d.new[spec.key] ?? 0), 0)
		}))
	);
	let metric = $derived(overview.surface.find((m) => m.key === dim));
</script>

<Cell
	id="changes"
	title="Attack surface changes"
	description="Rows held after each run, per day"
	href={ROUTES.surface(spec.tab, { [spec.queryParam]: 'is:new' })}
	hrefLabel="{spec.label} is:new"
	class={className}
>
	<ToggleGroup.Root
		type="single"
		size="sm"
		value={dim}
		onValueChange={(v) => v && (dim = v)}
		class="flex-wrap justify-start"
		aria-label="Dimension"
	>
		{#each totals as t (t.key)}
			<ToggleGroup.Item value={t.key} class="h-7 gap-1 px-2 text-xs">
				{t.label}
				<span class="text-muted-foreground tabular-nums">+{t.added.toLocaleString()}</span>
			</ToggleGroup.Item>
		{/each}
	</ToggleGroup.Root>
	{#key `${dim}:${window}`}
		<DailyArea {data} label={spec.label} height={190} />
	{/key}
	{#snippet footer()}
		<span>
			{added.toLocaleString()} added{#if hasRetired}, {retired.toLocaleString()} retired{/if}
			in {days} days
			{#if metric}· {metric.value.toLocaleString()} {spec.label.toLowerCase()} today{/if}
		</span>
	{/snippet}
</Cell>
