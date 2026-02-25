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
		hasMore?: boolean;
	}

	let {
		dayGroups,
		newEventIds = new Set(),
		tick = 0,
		isLoading = false,
		isEmpty = false,
		hasMore = false
	}: Props = $props();
</script>

{#if isLoading}
	<div class="space-y-5 pl-6">
		{#each { length: 4 } as _, i}
			<div class="relative">
				<div
					class="absolute -left-6 top-[5px] h-[9px] w-[9px] rounded-full bg-muted/50 animate-pulse"
				></div>
				<div class="space-y-1.5">
					<div
						class="h-3.5 rounded bg-muted/40 animate-pulse"
						style="width: {75 - i * 12}%; animation-delay: {i * 100}ms"
					></div>
					<div
						class="h-2.5 w-1/4 rounded bg-muted/25 animate-pulse"
						style="animation-delay: {i * 100 + 50}ms"
					></div>
				</div>
			</div>
		{/each}
	</div>
{:else if isEmpty}
	<div class="flex h-full flex-col items-center justify-center py-12 text-center">
		<div class="rounded-full bg-muted/20 p-3 mb-3">
			<Activity class="h-5 w-5 text-muted-foreground/25" />
		</div>
		<p class="text-[11px] text-muted-foreground/40">No activity yet</p>
	</div>
{:else}
	{#each dayGroups as group, gi (group.date)}
		<!-- Day separator — breaks the timeline -->
		<div class="flex items-center gap-2 {gi > 0 ? 'mt-4 mb-3' : 'mb-3'}">
			<div class="h-px flex-1 bg-border/40"></div>
			<span
				class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground/40 shrink-0 px-1"
			>
				{group.label}
			</span>
			<div class="h-px flex-1 bg-border/40"></div>
		</div>

		<!-- Continuous timeline track -->
		<div class="relative">
			<div class="absolute left-0 top-0 bottom-0 w-px bg-border/50"></div>

			{#each group.clusters as cluster (cluster.id)}
				<ActivityTimelineItem {cluster} {tick} isNew={newEventIds.has(cluster.items[0]?.id)} />
			{/each}
		</div>
	{/each}

	{#if hasMore}
		<div class="flex justify-center pt-3 pb-1">
			<div class="flex gap-1">
				{#each { length: 3 } as _, i}
					<div
						class="h-1 w-1 rounded-full bg-muted-foreground/15 animate-pulse"
						style="animation-delay: {i * 150}ms"
					></div>
				{/each}
			</div>
		</div>
	{/if}
{/if}
