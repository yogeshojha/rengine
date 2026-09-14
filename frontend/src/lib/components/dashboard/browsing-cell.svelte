<script lang="ts">
	import Cell from './cell.svelte';
	import DailyBars, { type DailyPoint } from './daily-bars.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { windowDays, type DashboardBrowsing, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		browsing: DashboardBrowsing;
		window: DashboardWindow;
		class?: string;
	}

	let { browsing, window, class: className = '' }: Props = $props();

	let days = $derived(windowDays(window));
	let data = $derived<DailyPoint[]>(
		browsing.daily.slice(-days).map((d) => ({ date: d.date, browsed: d.kinds.browsed ?? 0 }))
	);
	let inWindow = $derived(data.reduce((n, d) => n + (d.browsed as number), 0));
	const series = [{ key: 'browsed', label: 'Browsed', color: 'var(--series)' }];
	let tiles = $derived(
		[
			{
				key: 'browsed',
				label: 'Browsed',
				value: browsing.browsed,
				sub: 'endpoints',
				href: ROUTES.connectors('queue')
			},
			{
				key: 'unseen',
				label: 'Unseen by scans',
				value: browsing.unseen,
				sub: null,
				href: ROUTES.connectors('queue')
			},
			{
				key: 'params',
				label: 'New parameters',
				value: browsing.new_params,
				sub: null,
				href: ROUTES.connectors('queue')
			},
			{
				key: 'flagged',
				label: 'Flagged',
				value: browsing.flagged,
				sub: null,
				href: ROUTES.connectors('queue')
			}
		].filter((t) => t.value > 0)
	);
</script>

<Cell
	id="connectors"
	title="Browsing"
	description="Proxy traffic"
	href={ROUTES.connectors()}
	hrefLabel="Connectors"
	class={className}
>
	{#if tiles.length}
		<div class="grid grid-cols-2 gap-2">
			{#each tiles as t (t.key)}
				<a
					href={t.href}
					class="flex flex-col gap-0.5 rounded-lg border bg-muted/20 px-2.5 py-2 transition-colors hover:bg-muted/50"
				>
					<span class="text-2xs text-muted-foreground">{t.label}</span>
					<span class="flex items-baseline gap-1">
						<span class="text-lg leading-none font-semibold tracking-tight tabular-nums">
							{t.value.toLocaleString()}
						</span>
						{#if t.sub}<span class="text-2xs text-muted-foreground">{t.sub}</span>{/if}
					</span>
				</a>
			{/each}
		</div>
	{/if}
	{#if inWindow > 0}
		{#key window}
			<DailyBars {data} {series} height={84} />
		{/key}
	{/if}
	{#snippet footer()}
		<span>
			{browsing.connectors}
			{browsing.connectors === 1 ? 'connector' : 'connectors'}{#if browsing.last_seen_at}
				· last traffic {relativeTime(browsing.last_seen_at)}{/if}
		</span>
	{/snippet}
</Cell>
