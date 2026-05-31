<script lang="ts">
	import { fly } from 'svelte/transition';
	import { activityFeed, LEVEL_DOT } from '$lib/stores/activity-feed.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { Activity, Loader } from 'lucide-svelte';

	let latest = $derived(activityFeed.latest);
	let statusDot = $derived(
		sseStore.isConnected
			? 'bg-emerald-500'
			: sseStore.isReconnecting
				? 'bg-amber-500'
				: 'bg-muted-foreground/40'
	);
	// recompute relative time whenever the feed ticks
	let timeLabel = $derived.by(() => {
		void activityFeed.tick;
		return latest ? relativeTime(latest.timestamp) : '';
	});
</script>

<button
	type="button"
	data-activity-glance
	onclick={() => activityFeed.toggle()}
	title="Activity"
	class="group relative inline-flex h-8 max-w-[300px] items-center gap-2 rounded-full border border-border/60 bg-muted/30 pl-2 pr-2.5 text-xs transition-colors hover:bg-muted/60 {activityFeed.open
		? 'ring-1 ring-primary/30'
		: ''}"
>
	<span class="relative flex h-2 w-2 shrink-0">
		{#if activityFeed.isLive}
			<span
				class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"
			></span>
		{/if}
		<span class="relative inline-flex h-2 w-2 rounded-full {statusDot}"></span>
	</span>

	{#if activityFeed.runningCount > 0}
		<span class="hidden items-center gap-1.5 text-sky-600 dark:text-sky-400 sm:flex">
			<Loader class="h-3 w-3 animate-spin" />
			<span class="font-medium">{activityFeed.runningCount} running</span>
		</span>
		<Loader class="h-3.5 w-3.5 animate-spin text-sky-500 sm:hidden" />
	{:else if latest}
		<span class="hidden min-w-0 items-center gap-2 sm:flex">
			{#key latest.id}
				<span in:fly={{ y: -6, duration: 220 }} class="flex items-center gap-1.5 min-w-0">
					<span class="h-1 w-1 shrink-0 rounded-full {LEVEL_DOT[latest.level] ?? LEVEL_DOT.info}"
					></span>
					<span class="max-w-[180px] truncate text-foreground/70">{latest.title}</span>
				</span>
			{/key}
			<span class="shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground">
				{timeLabel}
			</span>
		</span>
		<Activity class="h-3.5 w-3.5 text-muted-foreground sm:hidden" />
	{:else}
		<Activity class="h-3.5 w-3.5 text-muted-foreground" />
		<span class="hidden text-muted-foreground sm:inline">Activity</span>
	{/if}

	{#if activityFeed.newCount > 0}
		<span
			in:fly={{ y: -4, duration: 180 }}
			class="ml-0.5 inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 px-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400"
		>
			{activityFeed.newCount}
		</span>
	{/if}
</button>
