<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { SCHEDULE_TYPE_BADGE, type ScheduleType } from '$lib/types/scan-schedule';
	import { formatTargetType, type TargetType } from '$lib/types/target';
	import type { ScanRead, ScanTargetTrend } from '$lib/types/scan';
	import TrendSpark from './trend-spark.svelte';

	const STALE_DAYS = 30;
	const DAY_MS = 86_400_000;

	interface Props {
		scan: ScanRead;
		showTarget: boolean;
		trend?: ScanTargetTrend;
		now: number;
		earlierOpen?: boolean;
		onEarlier?: () => void;
		onJump: (scanId: string) => void;
	}

	let { scan, showTarget, trend, now, earlierOpen = false, onEarlier, onJump }: Props = $props();

	let focused = $derived(scan.scope === 'focused');
	let schedule = $derived(
		scan.schedule_type ? (SCHEDULE_TYPE_BADGE[scan.schedule_type as ScheduleType] ?? null) : null
	);
	let age = $derived(
		Math.floor(
			(now - new Date(scan.completed_at ?? scan.started_at ?? scan.created_at).getTime()) / DAY_MS
		)
	);
	let earlier = $derived(scan.target_runs != null ? scan.target_runs - 1 : 0);
</script>

<div class="flex min-w-0 items-center gap-3">
	<div class="min-w-0 flex-1">
		<div class="flex min-w-0 items-center gap-1.5">
			<span class="truncate font-mono text-sm font-medium">
				{showTarget ? scan.execution_config.target_value : scan.engine_name}
			</span>
			{#if showTarget}
				<CopyButton
					value={scan.execution_config.target_value}
					class="shrink-0 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
				/>
			{/if}
		</div>
		<div
			class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-2xs text-muted-foreground"
		>
			{#if showTarget}
				<span class="rounded border border-border/70 px-1 font-mono uppercase">
					{formatTargetType(scan.execution_config.target_type as TargetType)}
				</span>
			{/if}
			{#if focused}
				<span>Focused · {scan.seed_count} {scan.seed_count === 1 ? 'asset' : 'assets'}</span>
			{/if}
			{#if scan.context_name}
				<span class="truncate">{scan.context_name}</span>
			{/if}
			{#if schedule}
				<span>{schedule}</span>
			{/if}
			{#if scan.target_runs != null && age > STALE_DAYS}
				<span class="font-medium text-warning">Stale · {age} days</span>
			{/if}
			{#if onEarlier && earlier > 0}
				<button
					type="button"
					class="inline-flex items-center gap-0.5 rounded px-0.5 font-medium text-foreground/80 hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					aria-expanded={earlierOpen}
					onclick={(e) => {
						e.stopPropagation();
						onEarlier?.();
					}}
				>
					<ChevronRight class="size-3 transition-transform {earlierOpen ? 'rotate-90' : ''}" />
					{earlier} earlier {earlier === 1 ? 'run' : 'runs'}
				</button>
			{/if}
			{#if scan.rescans && scan.rescans.total > 0}
				<span>{scan.rescans.total} {scan.rescans.total === 1 ? 'rescan' : 'rescans'}</span>
			{/if}
		</div>
	</div>
	{#if showTarget && trend}
		<TrendSpark points={trend.points} current={scan.id} {onJump} />
	{/if}
</div>
