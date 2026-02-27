<script lang="ts">
	import { Activity } from 'lucide-svelte';
	import ActivityTimelineItem from './activity-timeline-item.svelte';
	import type { ActivityDayGroup } from '$lib/types/activity';

	interface Props {
		dayGroups: ActivityDayGroup[];
		newEventIds?: Set<string>;
		tick?: number;
		isLoading?: boolean;
		isEmpty?: boolean;
	}

	let {
		dayGroups,
		newEventIds = new Set(),
		tick = 0,
		isLoading = false,
		isEmpty = false
	}: Props = $props();
</script>

{#if isLoading}
	<div class="relative pl-5">
		<div class="absolute left-0 top-0 bottom-4 w-px bg-border/40"></div>
		{#each { length: 4 } as _, i}
			<div class="relative pb-3">
				<span
					class="absolute left-0 top-[6px] h-[7px] w-[7px] -translate-x-1/2 rounded-full bg-muted animate-pulse"
				></span>
				<div class="space-y-1 py-0.5 px-1.5">
					<div class="h-3 rounded bg-muted/60 animate-pulse" style="width:{80 - i * 12}%"></div>
					<div class="h-2.5 w-16 rounded bg-muted/40 animate-pulse"></div>
				</div>
			</div>
		{/each}
	</div>
{:else if isEmpty}
	<div class="flex flex-col items-center justify-center py-10 text-center">
		<div class="mb-2 rounded-full bg-muted/30 p-3">
			<Activity class="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
		</div>
		<p class="text-xs font-medium text-muted-foreground">No activity yet</p>
		<p class="mt-0.5 text-[10px] text-muted-foreground/70">Events appear here in real time</p>
	</div>
{:else}
	{#each dayGroups as group, gi (group.date)}
		<div class="flex items-center gap-2 {gi > 0 ? 'mt-3 mb-2' : 'mb-2'}">
			<div class="h-px flex-1 bg-border/40"></div>
			<span
				class="text-[9px] font-semibold uppercase tracking-[0.1em] text-muted-foreground/70 px-1"
			>
				{group.label}
			</span>
			<div class="h-px flex-1 bg-border/40"></div>
		</div>

		<div class="relative">
			<div class="absolute left-0 top-0 bottom-1 w-px bg-border/40"></div>
			{#each group.clusters as cluster (cluster.id)}
				<ActivityTimelineItem {cluster} {tick} isNew={newEventIds.has(cluster.items[0]?.id)} />
			{/each}
		</div>
	{/each}
{/if}
