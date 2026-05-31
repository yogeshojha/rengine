<script lang="ts">
	import { Activity, SearchX, ShieldX } from 'lucide-svelte';
	import ActivityTimelineItem from './activity-timeline-item.svelte';
	import type { ActivityDayGroup } from '$lib/types/activity';
	import { activityFeed, FILTER_LABELS } from '$lib/stores/activity-feed.svelte';

	interface Props {
		dayGroups: ActivityDayGroup[];
		newEventIds?: Set<string>;
		runningIds?: Set<string>;
		tick?: number;
		isLoading?: boolean;
		isEmpty?: boolean;
	}

	let {
		dayGroups,
		newEventIds = new Set(),
		runningIds = new Set(),
		tick = 0,
		isLoading = false,
		isEmpty = false
	}: Props = $props();

	let empty = $derived.by(() => {
		if (activityFeed.search.trim())
			return {
				icon: SearchX,
				title: 'No matches',
				sub: `Nothing for “${activityFeed.search.trim()}”`
			};
		if (activityFeed.errorsOnly)
			return { icon: ShieldX, title: 'No errors', sub: 'Nothing has failed in this view' };
		if (activityFeed.filter !== 'all')
			return {
				icon: Activity,
				title: `No ${FILTER_LABELS[activityFeed.filter].toLowerCase()} yet`,
				sub: 'Events appear here in real time'
			};
		return { icon: Activity, title: 'No activity yet', sub: 'Events appear here in real time' };
	});
</script>

{#if isLoading}
	<div class="relative pl-[10px]">
		<div class="absolute left-[10px] top-0 bottom-4 w-px bg-border/40"></div>
		{#each { length: 4 } as _, i}
			<div class="relative flex gap-2.5 pb-3">
				<span class="z-[1] mt-px h-5 w-5 shrink-0 rounded-full bg-muted animate-pulse"></span>
				<div class="flex-1 space-y-1 py-0.5">
					<div class="h-3 rounded bg-muted/60 animate-pulse" style="width:{80 - i * 12}%"></div>
					<div class="h-2.5 w-16 rounded bg-muted/40 animate-pulse"></div>
				</div>
			</div>
		{/each}
	</div>
{:else if isEmpty}
	<div class="flex flex-col items-center justify-center py-12 text-center">
		<div class="mb-2 rounded-full bg-muted/30 p-3">
			<empty.icon class="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
		</div>
		<p class="text-xs font-medium text-muted-foreground">{empty.title}</p>
		<p class="mt-0.5 text-[10px] text-muted-foreground/70">{empty.sub}</p>
	</div>
{:else}
	{#each dayGroups as group, gi (group.date)}
		<div
			class="sticky top-0 z-10 -mx-3 flex items-center gap-2 bg-background/95 px-3 py-1.5 backdrop-blur {gi >
			0
				? 'mt-1'
				: ''}"
		>
			<div class="h-px flex-1 bg-border/40"></div>
			<span
				class="px-1 text-[9px] font-semibold uppercase tracking-[0.1em] text-muted-foreground/70"
			>
				{group.label}
			</span>
			<div class="h-px flex-1 bg-border/40"></div>
		</div>

		<div class="relative">
			<div class="absolute left-[10px] top-0 bottom-1 w-px bg-border/40"></div>
			{#each group.clusters as cluster (cluster.id)}
				<ActivityTimelineItem
					{cluster}
					{tick}
					{runningIds}
					isNew={newEventIds.has(cluster.items[0]?.id)}
				/>
			{/each}
		</div>
	{/each}
{/if}
