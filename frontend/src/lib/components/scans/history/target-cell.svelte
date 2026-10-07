<script lang="ts">
	import { REVEAL_SM } from '$lib/components/scans/results/table/columns';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { STALE_DAYS } from '$lib/config/dashboard';
	import { SCHEDULE_TYPE_BADGE, type ScheduleType } from '$lib/types/scan-schedule';
	import { formatTargetType, type TargetType } from '$lib/types/target';
	import type { ScanRead, ScanTargetTrend } from '$lib/types/scan';
	import { plural, pluralWord } from '$lib/utilities/strings';
	import TrendSpark from './trend-spark.svelte';

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
			<span
				class="truncate font-mono text-sm font-medium"
				title={showTarget ? scan.execution_config.target_value : scan.engine_name}
			>
				{showTarget ? scan.execution_config.target_value : scan.engine_name}
			</span>
			{#if showTarget}
				<CopyButton
					value={scan.execution_config.target_value}
					class="shrink-0 transition-opacity {REVEAL_SM}"
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
				<span>Focused · {plural(scan.seed_count, 'asset')}</span>
			{/if}
			{#if scan.context_name}
				<span class="truncate" title={scan.context_name}>{scan.context_name}</span>
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
					{earlier} earlier {pluralWord(earlier, 'run')}
				</button>
			{/if}
			{#if scan.rescans && scan.rescans.total > 0}
				<span>{plural(scan.rescans.total, 'rescan')}</span>
			{/if}
		</div>
	</div>
	{#if showTarget && trend}
		<TrendSpark points={trend.points} current={scan.id} {onJump} />
	{/if}
</div>
