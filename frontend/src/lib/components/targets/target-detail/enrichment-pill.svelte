<script lang="ts">
	import { TaskStatus } from '$lib/types/task-status';
	import { getFreshnessLevel, relativeTime } from '$lib/utilities/dates';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { TriangleAlert } from 'lucide-svelte';

	interface Props {
		label: string;
		status: TaskStatus;
		queriedAt?: string | null;
	}

	let { label, status, queriedAt = null }: Props = $props();

	const isStale = $derived(status === TaskStatus.SUCCESS && getFreshnessLevel(queriedAt) === 'stale');

	const state = $derived.by(() => {
		switch (status) {
			case TaskStatus.FAILED:
				return { dot: 'bg-destructive/70', time: 'Failed', tip: 'Enrichment failed' };
			case TaskStatus.QUERYING:
				return { dot: 'bg-chart-1/60 animate-pulse', time: 'Running', tip: 'Enrichment in progress' };
			case TaskStatus.PENDING:
				return { dot: 'bg-amber-500/50 animate-pulse', time: 'Queued', tip: 'Enrichment queued' };
			case TaskStatus.SKIPPED:
				return { dot: 'bg-muted-foreground/20', time: 'Skipped', tip: 'Not applicable' };
			default: {
				const t = queriedAt ? relativeTime(queriedAt) : '';
				return {
					dot: isStale ? 'bg-amber-500/60' : 'bg-muted-foreground/30',
					time: t,
					tip: t ? `Refreshed ${t}${isStale ? ' — consider refreshing' : ''}` : 'Completed'
				};
			}
		}
	});
</script>

<Tooltip.Root>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<Badge {...props} variant="outline" class="gap-1.5 border-border/60 font-normal">
				<span class="h-1.5 w-1.5 shrink-0 rounded-full {state.dot}"></span>
				<span class="text-[11px] font-medium text-foreground/80">{label}</span>
				{#if state.time}<span class="text-[11px] text-muted-foreground">· {state.time}</span>{/if}
				{#if isStale}<TriangleAlert class="h-3 w-3 text-amber-600 dark:text-amber-500" />{/if}
			</Badge>
		{/snippet}
	</Tooltip.Trigger>
	<Tooltip.Content>
		<p class="text-xs">{label}: {state.tip}</p>
	</Tooltip.Content>
</Tooltip.Root>
