<script lang="ts">
	import { severityLabel } from '$lib/config/vulnerabilities';
	import type { FindingStats, TimelineScan } from '$lib/types/timeline';
	import { formatMonthDay } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import ExposureCurve from './exposure-curve.svelte';

	interface Props {
		stats: FindingStats;
		scans: TimelineScan[];
		runs: number;
		highlight: number;
		onHover: (index: number) => void;
		onOpenScan: (scanId: string) => void;
	}

	let { stats, scans, runs, highlight, onHover, onOpenScan }: Props = $props();

	let previous = $derived.by(() => {
		const before = scans
			.slice(0, -1)
			.reverse()
			.find((s) => s.observation !== 'unobserved');
		return before?.started_at ? formatMonthDay(before.started_at) : '';
	});
	let delta = $derived(
		stats.open_delta == null || !previous
			? ''
			: `${stats.open_delta > 0 ? '+' : stats.open_delta < 0 ? '−' : ''}${Math.abs(stats.open_delta)} since ${previous}`
	);
	let openDetail = $derived(
		[delta, stats.untested ? `${stats.untested} absent, not tested` : '']
			.filter(Boolean)
			.join(' · ')
	);
	let window = $derived(
		runs > scans.length
			? `last ${plural(scans.length, 'run')}`
			: `in ${plural(scans.length, 'run')}`
	);
</script>

{#snippet stat(label: string, value: string, detail: string, tone = '')}
	<div class="flex min-w-0 flex-col gap-0.5">
		<span class="text-2xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
		<span class="text-2xl leading-none font-semibold tracking-tight tabular-nums {tone}"
			>{value}</span
		>
		<span class="truncate text-xs text-muted-foreground">{detail}</span>
	</div>
{/snippet}

<div class="flex flex-wrap items-stretch border-b">
	<div class="flex flex-wrap gap-7 border-border/60 px-5 py-4 lg:border-r">
		{@render stat(
			'Open now',
			stats.open_now == null ? 'Not scanned' : String(stats.open_now),
			stats.open_now == null ? '' : openDetail
		)}
		{@render stat(
			'Regressed',
			String(stats.regressed),
			window,
			stats.regressed ? 'text-destructive' : ''
		)}
		{@render stat(
			'Fixed',
			String(stats.fixed),
			stats.fixed_median_days == null ? '' : `median ${plural(stats.fixed_median_days, 'day')} open`
		)}
		{@render stat(
			'Oldest open',
			stats.oldest_open_days == null ? '0' : `${stats.oldest_open_days} d`,
			stats.oldest_open_name
				? `${stats.oldest_open_name} · ${severityLabel(stats.oldest_open_severity).toLowerCase()}`
				: ''
		)}
	</div>
	<div class="flex min-w-0 flex-1 items-center px-5 py-3">
		<ExposureCurve runs={stats.runs} {scans} {highlight} {onHover} {onOpenScan} />
	</div>
</div>
