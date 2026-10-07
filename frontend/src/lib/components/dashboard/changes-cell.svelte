<script lang="ts">
	import { useScopedRoutes } from './scope-links';
	import Cell from './cell.svelte';
	import DailyArea, { type DailyLevel } from './daily-area.svelte';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { SURFACE, SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
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

	let dim = $state<string>(SurfaceDimension.WEB_ASSETS);
	let spec = $derived(SURFACE[dim as SurfaceDimension]);
	let days = $derived(windowDays(window));
	let recent = $derived(bucketsSince(overview.daily, overview.since));
	let data = $derived<DailyLevel[]>(
		recent.map((d) => ({
			date: d.date,
			total: d.total[dim] ?? 0,
			added: d.new[dim] ?? 0,
			retired: d.retired[dim] ?? 0,
			runs: d.runs
		}))
	);
	let added = $derived(counts?.new.find((c) => c.key === dim) ?? null);
	let retired = $derived(overview.retired_in_window[dim] ?? 0);
	// dimensions that did not move stay out of the toggle, bar the one picked
	let totals = $derived(
		SURFACE_ORDER.map((spec) => ({
			key: spec.key,
			label: spec.label,
			added: counts?.new.find((c) => c.key === spec.key) ?? null
		})).filter(
			(t) =>
				!counts ||
				t.key === dim ||
				(t.added?.count ?? 0) > 0 ||
				(overview.retired_in_window[t.key] ?? 0) > 0
		)
	);
	let metric = $derived(overview.surface.find((m) => m.key === dim));
	let summary = $derived.by(() => {
		const moved = [
			added && `${cappedCount(added.count, added.capped)} added`,
			retired && `${retired.toLocaleString()} retired`
		].filter(Boolean);
		return [
			moved.length && `${moved.join(', ')} in ${days} days`,
			metric && `${metric.value.toLocaleString()} ${spec.label.toLowerCase()} today`
		]
			.filter(Boolean)
			.join(' · ');
	});
</script>

<Cell
	id="changes"
	description="Rows per day"
	href={added ? routes.rows(spec.key, added.query) : undefined}
	hrefLabel={added?.query}
	loading={loading && !counts}
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
				{#if t.added}
					<span class="text-muted-foreground tabular-nums"
						>+{cappedCount(t.added.count, t.added.capped)}</span
					>
				{/if}
			</ToggleGroup.Item>
		{/each}
	</ToggleGroup.Root>
	{#key `${dim}:${window}`}
		<DailyArea {data} label={spec.label} height={190} />
	{/key}
	{#snippet footer()}
		<span>{summary}</span>
	{/snippet}
</Cell>
