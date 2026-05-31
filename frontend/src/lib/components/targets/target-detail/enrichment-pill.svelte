<script lang="ts">
	import { TaskStatus } from '$lib/types/task-status';
	import { getTaskStatusConfig } from '$lib/config/task-status';
	import { getFreshnessLevel, getFreshnessColors, relativeTime } from '$lib/utilities/dates';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';

	interface Props {
		label: string;
		status: TaskStatus;
		queriedAt?: string | null;
	}

	let { label, status, queriedAt = null }: Props = $props();

	const pillState = $derived.by(() => {
		const statusConfig = getTaskStatusConfig(status);

		if (status !== TaskStatus.SUCCESS) {
			return {
				dotClass: statusConfig.dotClass,
				textClass: statusConfig.textClass,
				borderClass: statusConfig.borderClass,
				timeText: statusConfig.label,
				tooltip: `${label}: ${statusConfig.label}`
			};
		}

		const freshness = getFreshnessLevel(queriedAt);
		const colors = getFreshnessColors(freshness);
		const time = relativeTime(queriedAt);

		return {
			dotClass: colors.dot,
			textClass: colors.text,
			borderClass: colors.border,
			timeText: time,
			tooltip: `${label}: Refreshed ${time}${freshness === 'stale' ? ' — consider refreshing' : ''}`
		};
	});

	const isStale = $derived(
		status === TaskStatus.SUCCESS && getFreshnessLevel(queriedAt) === 'stale'
	);
</script>

<Tooltip.Root>
	<Tooltip.Trigger>
		<div
			class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 transition-colors {pillState.borderClass}"
		>
			<div class="h-1.5 w-1.5 rounded-full shrink-0 {pillState.dotClass}"></div>
			<span class="text-[11px] font-medium {pillState.textClass}">
				{label}
			</span>
			<span class="text-[11px] text-muted-foreground">· {pillState.timeText}</span>
			{#if isStale}
				<span class="text-[10px] text-amber-600 dark:text-amber-400 font-medium">⚠</span>
			{/if}
		</div>
	</Tooltip.Trigger>
	<Tooltip.Content>
		<p class="text-xs">{pillState.tooltip}</p>
	</Tooltip.Content>
</Tooltip.Root>
