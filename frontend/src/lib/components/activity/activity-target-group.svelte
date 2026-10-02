<script lang="ts">
	import { goto } from '$app/navigation';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Hint from '$lib/components/hint.svelte';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import FolderKanban from '@lucide/svelte/icons/folder-kanban';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { relativeTime } from '$lib/utilities/dates';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { activityFeed } from '$lib/stores/activity-feed.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { UNSCOPED_GROUP_KEY, type ActivityTargetGroup } from '$lib/types/activity';
	import ActivityTimelineItem from './activity-timeline-item.svelte';

	interface Props {
		group: ActivityTargetGroup;
		newEventIds?: Set<string>;
		runningIds?: Set<string>;
		tick?: number;
		onRescan?: (targetId: string) => void;
	}

	let {
		group,
		newEventIds = new Set(),
		runningIds = new Set(),
		tick = 0,
		onRescan
	}: Props = $props();

	let unscoped = $derived(group.key === UNSCOPED_GROUP_KEY);
	let collapsed = $derived(activityFeed.collapsedGroups.has(group.key));
	let live = $derived(
		!!group.targetId && liveScans.scans.some((s) => s.target_id === group.targetId)
	);
	let fresh = $derived(group.clusters.some((c) => newEventIds.has(c.items[0]?.id)));
	let timeAgo = $derived.by(() => {
		void tick;
		return relativeTime(group.latest);
	});
	let eventCount = $derived(group.clusters.reduce((n, c) => n + c.items.length, 0));

	function openTarget() {
		if (group.targetId) {
			goto(ROUTES.target(group.targetId));
			activityFeed.setOpen(false);
		}
	}
</script>

<section class="mb-1" aria-label={group.label}>
	<div
		class="group/head sticky top-0 z-10 -mx-1 flex w-[calc(100%+8px)] items-center gap-1 rounded-md bg-background/95 backdrop-blur transition-colors hover:bg-accent/50"
	>
		<button
			type="button"
			onclick={() => activityFeed.toggleGroup(group.key)}
			aria-expanded={!collapsed}
			class="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1 py-1.5 text-left"
		>
			<span
				class="flex size-5 shrink-0 items-center justify-center rounded-md {live
					? 'bg-info/10 text-info'
					: 'bg-muted text-muted-foreground'}"
			>
				{#if live}
					<Spinner class="size-3" />
				{:else if unscoped}
					<FolderKanban class="size-3" />
				{:else}
					<Crosshair class="size-3" />
				{/if}
			</span>

			<span
				class="min-w-0 flex-1 truncate text-xs font-medium text-foreground {unscoped
					? ''
					: 'font-mono'}"
			>
				{group.label}
			</span>

			<span class="flex shrink-0 items-center gap-1.5">
				{#if group.errors > 0}
					<span
						class="rounded-full bg-destructive/10 px-1.5 font-mono text-2xs font-semibold text-destructive tabular-nums"
					>
						{group.errors} err
					</span>
				{/if}
				{#if fresh}
					<span class="size-1.5 rounded-full bg-info"></span>
				{/if}
				<span class="font-mono text-2xs text-muted-foreground tabular-nums">
					{collapsed ? `${eventCount} · ${timeAgo}` : timeAgo}
				</span>
				<ChevronDown
					class="size-3 text-muted-foreground transition-transform duration-150 {collapsed
						? '-rotate-90'
						: ''}"
				/>
			</span>
		</button>
		{#if group.targetId}
			<Hint text="Open target" side="left">
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						aria-label="Open target"
						onclick={openTarget}
						class="mr-1 shrink-0 rounded p-0.5 text-muted-foreground opacity-0 transition-opacity group-hover/head:opacity-100 hover:text-foreground focus-visible:opacity-100"
					>
						<ArrowUpRight class="size-3" />
					</button>
				{/snippet}
			</Hint>
		{/if}
	</div>

	{#if !collapsed}
		<div class="relative pt-1 pl-1">
			<div class="absolute top-1 bottom-1 left-[14px] w-px bg-border/40"></div>
			{#each group.clusters as cluster (cluster.id)}
				<ActivityTimelineItem
					{cluster}
					{tick}
					{runningIds}
					{onRescan}
					inGroup={!unscoped}
					isNew={newEventIds.has(cluster.items[0]?.id)}
				/>
			{/each}
		</div>
	{/if}
</section>
