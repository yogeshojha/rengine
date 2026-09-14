<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import { elapsedSeconds, formatSeconds } from '$lib/utilities/scan-status';
	import { relativeTime } from '$lib/utilities/dates';
	import type { DashboardOverview, DashboardPrograms } from '$lib/types/dashboard';
	import type { ThreatIntelStatus } from '$lib/types/threat-intel';

	interface Props {
		overview: DashboardOverview;
		intel: ThreatIntelStatus | null;
		programs: DashboardPrograms | null;
		now: number;
		class?: string;
	}

	let { overview, intel, programs, now, class: className = '' }: Props = $props();

	const FILL: Record<string, string> = {
		[SurfaceDimension.WEB_ASSETS]: 'var(--chart-1)',
		[SurfaceDimension.ENDPOINTS]: 'var(--chart-4)',
		[SurfaceDimension.SERVICES]: 'var(--chart-3)',
		[SurfaceDimension.IPS]: 'var(--chart-2)',
		[SurfaceDimension.SOFTWARE]: 'var(--series)'
	};
	const MAX_RUNS = 3;

	let liveCount = $derived(overview.funnel.steps.find((s) => s.key === 'live')?.count ?? 0);
	interface Row {
		key: string;
		label: string;
		value: number;
		sub: string | null;
		href: string;
		fill: string;
		ring: boolean;
	}
	let rows = $derived.by<Row[]>(() => {
		const out: Row[] = [
			{
				key: 'targets',
				label: 'Targets',
				value: overview.targets_total,
				sub: `${overview.targets_scanned} scanned`,
				href: String(ROUTES.targets),
				fill: 'var(--series)',
				ring: false
			}
		];
		for (const spec of SURFACE_ORDER) {
			const key = spec.key;
			const metric = overview.surface.find((m) => m.key === key);
			if (!metric) continue;
			let sub: string | null = null;
			if (key === SurfaceDimension.WEB_ASSETS && liveCount)
				sub = `${liveCount.toLocaleString()} answering`;
			if (key === SurfaceDimension.SERVICES && overview.exposure.sensitive)
				sub = `${overview.exposure.sensitive.toLocaleString()} sensitive`;
			if (key === SurfaceDimension.VULNERABILITIES) {
				const crit = overview.risk.by_severity.find((s) => s.severity === 'critical')?.count ?? 0;
				sub = crit ? `${crit.toLocaleString()} critical` : null;
			}
			out.push({
				key,
				label: spec.label,
				value: metric.value,
				sub,
				href: ROUTES.surface(spec.tab),
				fill: FILL[key] ?? 'var(--series)',
				ring: key === SurfaceDimension.VULNERABILITIES
			});
		}
		return out;
	});

	let names = $derived(new SvelteMap(overview.targets.map((t) => [t.id, t.value])));
	let running = $derived(liveScans.scans);
	let overflow = $derived(running.length > MAX_RUNS);
	let next = $derived.by(() => {
		const upcoming = scanSchedulesStore.schedules
			.filter((s) => s.next_run_at && s.status === 'active')
			.sort((a, b) => (a.next_run_at! < b.next_run_at! ? -1 : 1));
		return upcoming[0] ?? null;
	});
	let feedsAt = $derived.by(() => {
		const stamps = (intel?.feeds ?? []).map((f) => f.last_synced_at).filter(Boolean) as string[];
		return stamps.length ? stamps.sort().at(-1)! : null;
	});
	let unscheduled = $derived(overview.targets_total - overview.targets_monitored);
</script>

<Cell id="inventory" title="Inventory" class={className}>
	<div class="grid grid-cols-2 gap-x-4 gap-y-2.5">
		{#each rows as r (r.key)}
			<Hint text="Open {r.label}">
				{#snippet child(props)}
					<a
						{...props}
						href={r.href}
						class="group flex min-w-0 flex-col gap-0.5 rounded-md transition-colors hover:bg-muted/40 -mx-1.5 px-1.5 py-0.5"
					>
						<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
							{#if r.ring}
								<span class="size-2 shrink-0 rounded-full border-[1.5px] border-destructive"></span>
							{:else}
								<span class="size-2 shrink-0 rounded-full" style="background:{r.fill}"></span>
							{/if}
							<span class="truncate group-hover:text-foreground">{r.label}</span>
						</span>
						<span class="flex items-baseline gap-1.5">
							<span class="text-lg leading-none font-semibold tracking-tight tabular-nums">
								{r.value.toLocaleString()}
							</span>
							{#if r.sub}<span class="truncate text-2xs text-muted-foreground">{r.sub}</span>{/if}
						</span>
					</a>
				{/snippet}
			</Hint>
		{/each}
	</div>

	<div class="mt-1 flex flex-col gap-2">
		<span
			class="flex items-baseline justify-between text-2xs font-medium tracking-wider text-muted-foreground uppercase"
		>
			<span>{running.length ? 'Running now' : 'Next run'}</span>
			{#if overflow}
				<a href={ROUTES.scans} class="tracking-normal normal-case hover:text-foreground">
					{running.length} running
				</a>
			{/if}
		</span>
		{#if running.length}
			<ScrollArea class={overflow ? 'h-[5.25rem]' : ''}>
				<ul class="flex flex-col gap-1.5">
					{#each running as scan (scan.id)}
						{@const run = liveScans.runFor(scan.id)}
						{@const elapsed = elapsedSeconds(scan, now)}
						<li>
							<a href={ROUTES.scan(scan.id)} class="flex items-center gap-2 text-sm">
								<span
									class="size-1.5 shrink-0 rounded-full bg-chart-1 shadow-[0_0_0_3px_color-mix(in_oklch,var(--chart-1)_22%,transparent)]"
								></span>
								<span class="min-w-0 flex-1 truncate">
									<span class="font-medium">{names.get(scan.target_id) ?? scan.engine_name}</span>
									{#if run?.stage}<span class="text-muted-foreground">
											· {run.stage.title}</span
										>{/if}
								</span>
								{#if elapsed !== null}
									<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
										{formatSeconds(elapsed)}
									</span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			</ScrollArea>
		{/if}
		{#if next}
			<a href={ROUTES.schedules} class="flex items-center gap-2 text-sm">
				<span class="size-1.5 shrink-0 rounded-full bg-muted-foreground/60"></span>
				<span class="min-w-0 flex-1 truncate">
					<span class="font-medium">{next.targets[0]?.target_value ?? next.name}</span>
					{#if next.targets.length > 1}
						<span class="text-muted-foreground"> · {next.targets.length} targets</span>
					{/if}
				</span>
				<span class="shrink-0 text-xs text-muted-foreground">
					{relativeTime(next.next_run_at!)}
				</span>
			</a>
		{:else if !running.length}
			<span class="text-sm text-muted-foreground">No schedule</span>
		{/if}
	</div>

	{#snippet footer()}
		{#if programs}
			<span>
				{programs.watches.stream_running
					? `CT stream listening · ${programs.watches.stream_certificates.toLocaleString()} certificates`
					: 'CT stream stopped'}
			</span>
		{:else if feedsAt}
			<span>Feeds updated {relativeTime(feedsAt)}</span>
		{/if}
		{#if unscheduled > 0}
			<a href={ROUTES.schedules} class="font-medium text-foreground">
				{unscheduled} not on a schedule
			</a>
		{/if}
	{/snippet}
</Cell>
