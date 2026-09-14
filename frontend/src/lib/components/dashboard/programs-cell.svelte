<script lang="ts">
	import { untrack } from 'svelte';
	import Cell from './cell.svelte';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { PROGRAM_EVENT_FILL } from '$lib/config/dashboard';
	import { windowDays, type DashboardPrograms, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		programs: DashboardPrograms;
		window: DashboardWindow;
		class?: string;
	}

	let { programs, window, class: className = '' }: Props = $props();

	$effect(() => {
		untrack(() => bountyVocabulary.load());
	});

	const KINDS = Object.keys(PROGRAM_EVENT_FILL);
	let days = $derived(windowDays(window));
	let recent = $derived(programs.events_daily.slice(-days));
	let data = $derived<DailyPoint[]>(
		recent.map((d) => ({
			date: d.date,
			...Object.fromEntries(KINDS.map((k) => [k, d.kinds[k] ?? 0]))
		}))
	);
	let totals = $derived(
		KINDS.map((k) => ({
			key: k,
			label: bountyVocabulary.eventLabel(k),
			color: PROGRAM_EVENT_FILL[k],
			count: programs.events_in_window[k] ?? 0
		}))
	);
	let series = $derived(
		totals.filter((t) => t.count > 0).map((t) => ({ key: t.key, label: t.label, color: t.color }))
	);
	let inWindow = $derived(Object.values(programs.events_in_window).reduce((a, b) => a + b, 0));
	let platforms = $derived(
		Object.entries(programs.by_platform)
			.sort((a, b) => b[1] - a[1])
			.map(([key, n]) => `${bountyVocabulary.label(key)} ${n.toLocaleString()}`)
			.join(' · ')
	);
</script>

<Cell
	id="programs"
	title="Platform events"
	description="Programs and scope changes per day"
	href={ROUTES.bountyHubTab('updates')}
	hrefLabel="{programs.programs_total.toLocaleString()} programs"
	class={className}
>
	<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
		{#each totals as t (t.key)}
			<div class="flex flex-col gap-0.5 rounded-lg border bg-muted/20 px-2.5 py-2">
				<span class="flex items-center gap-1.5 text-2xs text-muted-foreground">
					<span class="size-1.5 rounded-full" style="background:{t.color}"></span>
					<span class="truncate">{t.label}</span>
				</span>
				<span class="text-lg leading-none font-semibold tracking-tight tabular-nums">
					{t.count.toLocaleString()}
				</span>
			</div>
		{/each}
	</div>
	{#if inWindow > 0}
		{#key window}
			<DailyBars {data} {series} height={130} />
		{/key}
	{/if}
	{#snippet footer()}
		<span>{platforms}</span>
	{/snippet}
</Cell>
