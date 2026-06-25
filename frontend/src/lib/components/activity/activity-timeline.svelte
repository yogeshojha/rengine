<script lang="ts">
	import Activity from '@lucide/svelte/icons/activity';
	import SearchX from '@lucide/svelte/icons/search-x';
	import ShieldX from '@lucide/svelte/icons/shield-x';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty/index.js';
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
		{#each { length: 4 } as _, i (i)}
			<div class="relative flex gap-2.5 pb-3">
				<Skeleton class="z-[1] mt-px h-5 w-5 shrink-0 rounded-full" />
				<div class="flex-1 space-y-1 py-0.5">
					<Skeleton class="h-3 rounded" style="width:{80 - i * 12}%" />
					<Skeleton class="h-2.5 w-16 rounded" />
				</div>
			</div>
		{/each}
	</div>
{:else if isEmpty}
	<Empty.Root class="gap-0 border-none p-0 py-12">
		<Empty.Header class="gap-0">
			<Empty.Media class="mb-2 rounded-full bg-muted/30 p-3">
				<empty.icon class="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
			</Empty.Media>
			<Empty.Title class="text-xs font-medium text-muted-foreground">{empty.title}</Empty.Title>
			<Empty.Description class="mt-0.5 text-[10px] text-muted-foreground/70"
				>{empty.sub}</Empty.Description
			>
		</Empty.Header>
	</Empty.Root>
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
