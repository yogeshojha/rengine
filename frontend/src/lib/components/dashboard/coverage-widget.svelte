<script lang="ts">
	import Play from '@lucide/svelte/icons/play';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Radar from '@lucide/svelte/icons/radar';
	import Clock from '@lucide/svelte/icons/clock';
	import RadioTower from '@lucide/svelte/icons/radio-tower';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import Widget from './widget.svelte';
	import { ROUTES } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';
	import { MS_PER_DAY } from '$lib/utilities/dates';
	import { windowText, type DashboardOverview, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		liveCount: number;
		onScan: (ids: string[]) => void;
		onSchedule: (ids: string[]) => void;
		class?: string;
	}

	let { overview, window, liveCount, onScan, onSchedule, class: className = '' }: Props = $props();

	const FRESH_DAYS = 7;
	const STALE_DAYS = 30;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let days = $derived(window === '30d' ? 30 : 7);
	let recent = $derived(overview.daily.slice(-days));
	let maxRuns = $derived(Math.max(1, ...recent.map((d) => d.runs)));
	let runsTotal = $derived(recent.reduce((n, d) => n + d.runs, 0));
	let failedTotal = $derived(recent.reduce((n, d) => n + d.failed, 0));

	let buckets = $derived.by(() => {
		const now = Date.now();
		const out = { fresh: 0, aging: 0, stale: 0, never: 0 };
		for (const t of overview.targets) {
			if (!t.last_scan_at) out.never += 1;
			else {
				const age = (now - new Date(t.last_scan_at).getTime()) / MS_PER_DAY;
				if (age <= FRESH_DAYS) out.fresh += 1;
				else if (age <= STALE_DAYS) out.aging += 1;
				else out.stale += 1;
			}
		}
		return out;
	});
	let scanned = $derived(buckets.fresh + buckets.aging + buckets.stale);
	let segments = $derived(
		[
			{
				key: 'fresh',
				label: `Scanned in the last ${FRESH_DAYS} days`,
				n: buckets.fresh,
				color: 'var(--chart-2)'
			},
			{
				key: 'aging',
				label: `Scanned ${FRESH_DAYS} to ${STALE_DAYS} days ago`,
				n: buckets.aging,
				color: 'var(--chart-4)'
			},
			{
				key: 'stale',
				label: `Last scanned over ${STALE_DAYS} days ago`,
				n: buckets.stale,
				color: 'var(--destructive)'
			}
		].filter((s) => s.n > 0)
	);

	let staleIds = $derived(overview.stale.map((t) => t.target_id));
	let neverIds = $derived(overview.never_scanned.map((t) => t.target_id));
	let unmonitored = $derived(overview.targets.filter((t) => !t.monitored).map((t) => t.id));

	interface Row {
		key: string;
		icon: IconComponent;
		label: string;
		count: number;
		tone: string;
		action?: { label: string; run: () => void };
		href?: string;
	}
	let rows = $derived.by<Row[]>(() => {
		const out: Row[] = [];
		if (liveCount > 0)
			out.push({
				key: 'live',
				icon: RadioTower,
				label: 'Running',
				count: liveCount,
				tone: 'text-info',
				href: ROUTES.scans
			});
		if (neverIds.length)
			out.push({
				key: 'never',
				icon: Radar,
				label: 'Never scanned',
				count: neverIds.length,
				tone: 'text-destructive',
				action: { label: 'Scan', run: () => onScan(neverIds) }
			});
		if (staleIds.length)
			out.push({
				key: 'stale',
				icon: Clock,
				label: `Not scanned in ${STALE_DAYS} days`,
				count: staleIds.length,
				tone: 'text-warning',
				action: { label: 'Scan', run: () => onScan(staleIds) }
			});
		if (unmonitored.length)
			out.push({
				key: 'unmonitored',
				icon: CalendarClock,
				label: 'Not scheduled',
				count: unmonitored.length,
				tone: 'text-warning',
				action: { label: 'Schedule', run: () => onSchedule(unmonitored) }
			});
		if (overview.failed_runs.length)
			out.push({
				key: 'failed',
				icon: CircleX,
				label: 'Last run failed',
				count: overview.failed_runs.length,
				tone: 'text-destructive',
				href: ROUTES.scans
			});
		return out;
	});
</script>

<Widget title="Coverage" class={className} href={ROUTES.scans} hrefLabel="Runs">
	<div class="flex flex-col gap-4 px-5 py-4">
		<div class="flex flex-col gap-2">
			<div class="flex items-baseline justify-between text-xs">
				<span class="text-muted-foreground">
					{plural(scanned, 'target', 'targets')} scanned
					{#if buckets.never}<span> · {buckets.never} never scanned</span>{/if}
				</span>
				<span class="font-medium tabular-nums">
					{overview.targets_monitored} of {overview.targets_total} monitored
				</span>
			</div>
			{#if segments.length}
				<div class="flex h-2 w-full gap-px overflow-hidden rounded-full bg-muted">
					{#each segments as s (s.key)}
						<Hint text="{plural(s.n, 'target', 'targets')} · {s.label}">
							{#snippet child(props)}
								<span
									{...props}
									class="block h-full"
									style="width:{(s.n / Math.max(1, overview.targets_total)) *
										100}%;background:{s.color}"
								></span>
							{/snippet}
						</Hint>
					{/each}
				</div>
				<div class="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
					{#each segments as s (s.key)}
						<span class="flex items-center gap-1.5">
							<span class="size-2 rounded-full" style="background:{s.color}"></span>
							{s.label.replace('Scanned ', '').replace('Last scanned ', '')}
							<span class="font-medium text-foreground tabular-nums">{s.n}</span>
						</span>
					{/each}
				</div>
			{/if}
		</div>

		{#if rows.length}
			<ul class="flex flex-col divide-y divide-border/60">
				{#each rows as r (r.key)}
					<li class="flex items-center gap-2.5 py-2 first:pt-0 last:pb-0">
						<r.icon class="size-3.5 shrink-0 {r.tone}" />
						<span class="min-w-0 flex-1 truncate text-sm">{r.label}</span>
						<span class="text-sm font-semibold tabular-nums">{r.count.toLocaleString()}</span>
						{#if r.action}
							<Button
								variant="outline"
								size="sm"
								class="h-7 gap-1 px-2 text-xs"
								onclick={r.action.run}
							>
								{#if r.key === 'unmonitored'}<CalendarClock class="size-3" />{:else}<Play
										class="size-3"
									/>{/if}
								{r.action.label}
							</Button>
						{:else if r.href}
							<a
								href={r.href}
								class="text-xs text-muted-foreground hover:text-foreground hover:underline"
							>
								View
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}

		<div class="flex flex-col gap-1.5">
			<div class="flex items-baseline justify-between text-xs">
				<span class="text-muted-foreground">Runs in the {windowText(window)}</span>
				<span class="tabular-nums">
					<span class="font-medium">{runsTotal}</span>
					{#if failedTotal}<span class="text-destructive"> · {failedTotal} failed</span>{/if}
				</span>
			</div>
			<div class="flex h-6 items-end gap-1">
				{#each recent as d (d.date)}
					<Hint
						text="{d.date} · {plural(d.runs, 'run', 'runs')}{d.failed
							? ` · ${d.failed} failed`
							: ''}"
					>
						{#snippet child(props)}
							<span {...props} class="flex h-full flex-1 items-end">
								<span
									class="block w-full rounded-sm {d.failed ? 'bg-destructive/70' : 'bg-chart-1/70'}"
									style="height:{d.runs
										? Math.max(12, (d.runs / maxRuns) * 100)
										: 4}%;opacity:{d.runs ? 1 : 0.25}"
								></span>
							</span>
						{/snippet}
					</Hint>
				{/each}
			</div>
		</div>
	</div>
</Widget>
