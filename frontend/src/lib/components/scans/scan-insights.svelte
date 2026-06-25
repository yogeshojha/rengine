<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Clock from '@lucide/svelte/icons/clock';
	import { relativeTime } from '$lib/utilities/dates';
	import type { ScanChanges, ScanChangeWindow, ScanStats, ScanStatus } from '$lib/types/scan';
	import ScanChangesHero from './scan-changes-hero.svelte';
	import ScanActivityChart from './scan-activity-chart.svelte';

	interface Props {
		stats: ScanStats | null;
		changes: ScanChanges | null;
		changeWindow: ScanChangeWindow;
		onWindow: (w: ScanChangeWindow) => void;
		onFilterStatus?: (statuses: ScanStatus[]) => void;
	}

	let { stats, changes, changeWindow, onWindow, onFilterStatus }: Props = $props();

	let total = $derived(stats?.total ?? 0);
	let active = $derived(stats ? stats.by_status.running + stats.by_status.pending : 0);
	let successPct = $derived(
		stats?.success_rate != null ? Math.round(stats.success_rate * 100) : null
	);
	let lastScan = $derived(stats?.last_scan_at ? relativeTime(stats.last_scan_at) : '—');
</script>

<div class="space-y-3">
	<ScanChangesHero {changes} window={changeWindow} {onWindow} />

	<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		<div class="rounded-lg border border-border p-3">
			<div class="text-lg font-semibold tabular-nums">{total}</div>
			<div class="text-xs text-muted-foreground">Total scans</div>
		</div>
		<button
			type="button"
			class="rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/40 disabled:cursor-default disabled:hover:bg-transparent"
			disabled={active === 0 || !onFilterStatus}
			onclick={() => onFilterStatus?.(['running', 'pending'])}
		>
			<div class="text-lg font-semibold tabular-nums {active > 0 ? 'text-warning' : ''}">
				{active}
			</div>
			<div class="text-xs text-muted-foreground">In progress</div>
		</button>
		<div class="rounded-lg border border-border p-3">
			<div class="flex items-center gap-1 text-lg font-semibold tabular-nums">
				<CircleCheck class="h-3.5 w-3.5 text-muted-foreground" />
				{successPct != null ? `${successPct}%` : '—'}
			</div>
			<div class="text-xs text-muted-foreground">Success rate</div>
		</div>
		<div class="rounded-lg border border-border p-3">
			<div class="flex items-center gap-1 text-lg font-semibold">
				<Clock class="h-3.5 w-3.5 text-muted-foreground" />
				<span class="truncate">{lastScan}</span>
			</div>
			<div class="text-xs text-muted-foreground">Last scan</div>
		</div>
	</div>

	<ScanActivityChart daily={stats?.daily ?? []} />
</div>
