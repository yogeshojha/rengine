<script lang="ts">
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { WatchHostState } from '$lib/types/watch';
	import { windowDays, type DashboardWatches, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		watches: DashboardWatches;
		window: DashboardWindow;
		class?: string;
	}

	let { watches, window, class: className = '' }: Props = $props();

	let days = $derived(windowDays(window));
	let data = $derived<DailyPoint[]>(
		watches.daily.slice(-days).map((d) => ({
			date: d.date,
			seen: d.kinds.seen ?? 0,
			alerted: d.kinds.alerted ?? 0
		}))
	);
	let seen = $derived(data.reduce((n, d) => n + (d.seen as number), 0));
	const series = [
		{ key: 'seen', label: 'Names seen', color: 'var(--series)' },
		{ key: 'alerted', label: 'Alerted', color: 'var(--destructive)' }
	];
	let ladder = $derived(watches.ladder.filter((s) => s.count > 0));
	let max = $derived(Math.max(1, ...ladder.map((s) => s.count)));
</script>

<Cell
	id="watches"
	title="Watched programs"
	description="Certificate names per day"
	href={ROUTES.bountyHubTab('watching')}
	hrefLabel="{watches.total} {watches.total === 1 ? 'watch' : 'watches'}"
	class={className}
>
	{#if seen > 0}
		{#key window}
			<DailyBars {data} {series} height={110} />
		{/key}
		<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
			{#each series as s (s.key)}
				<span class="flex items-center gap-1.5">
					<span class="size-2.5 rounded-[2px]" style="background:{s.color}"></span>{s.label}
				</span>
			{/each}
		</div>
	{/if}
	{#if ladder.length}
		<ul class="flex flex-col gap-1.5 rounded-lg border bg-muted/20 px-3 py-2.5">
			{#each ladder as s (s.state)}
				<li class="grid grid-cols-[6rem_1fr_2.5rem] items-center gap-2.5 text-xs">
					<Hint text="{s.count.toLocaleString()} {s.label.toLowerCase()}">
						{#snippet child(props)}
							<span {...props} class="truncate text-muted-foreground">{s.label}</span>
						{/snippet}
					</Hint>
					<span class="h-2.5 overflow-hidden rounded-[3px]">
						<span
							class="block h-full rounded-[3px] {s.state === WatchHostState.Alerted
								? 'bg-destructive'
								: 'bg-series'}"
							style="width:{Math.max(2, (s.count / max) * 100)}%"
						></span>
					</span>
					<span class="text-right font-medium tabular-nums">{s.count.toLocaleString()}</span>
				</li>
			{/each}
		</ul>
	{/if}
	{#snippet footer()}
		{#if watches.latest_alert}
			<a href={ROUTES.bountyWatch(watches.latest_alert.watch_id)} class="truncate">
				Latest <span class="font-mono text-foreground">{watches.latest_alert.name}</span> ·
				{watches.latest_alert.program_name} · {relativeTime(watches.latest_alert.at)}
			</a>
		{:else}
			<span>
				{watches.stream_running
					? 'Stream listening'
					: 'Stream stopped'}{#if watches.last_certificate_at}
					· last certificate {relativeTime(watches.last_certificate_at)}{/if}
			</span>
		{/if}
	{/snippet}
</Cell>
