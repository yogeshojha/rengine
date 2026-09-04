<script lang="ts">
	import { fly } from 'svelte/transition';
	import { activityFeed, LEVEL_DOT } from '$lib/stores/activity-feed.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import Activity from '@lucide/svelte/icons/activity';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';

	let latest = $derived(activityFeed.latest);
	let statusDot = $derived(
		sseStore.isConnected
			? 'bg-foreground'
			: sseStore.isReconnecting
				? 'bg-warning'
				: 'bg-muted-foreground/40'
	);
	let timeLabel = $derived.by(() => {
		void activityFeed.tick;
		return latest ? relativeTime(latest.timestamp) : '';
	});
</script>

<Hint text="Activity">
	{#snippet child(props)}
		<button
			{...props}
			type="button"
			aria-label="Activity"
			data-activity-glance
			onclick={() => activityFeed.toggle()}
			class="group relative inline-flex h-8 max-w-[300px] items-center gap-2 rounded-full border border-border/60 bg-muted/30 pl-2 pr-2.5 text-xs transition-colors hover:bg-muted/60 {activityFeed.open
				? 'ring-1 ring-primary/30'
				: ''}"
		>
			<span class="relative flex h-2 w-2 shrink-0">
				{#if activityFeed.isLive}
					<span
						class="absolute inline-flex h-full w-full animate-ping rounded-full bg-chart-1 opacity-75"
					></span>
				{/if}
				<span class="relative inline-flex h-2 w-2 rounded-full {statusDot}"></span>
			</span>

			{#if liveScans.hasLive}
				{@const solo = liveScans.count === 1 ? liveScans.scans[0] : null}
				{@const soloStage = solo ? liveScans.runFor(solo.id)?.stage?.title : null}
				<span class="hidden min-w-0 items-center gap-1.5 text-info sm:flex">
					<Spinner class="h-3 w-3 shrink-0" />
					{#if solo}
						<span class="max-w-[140px] truncate font-mono text-foreground/80"
							>{solo.execution_config.target_value}</span
						>
						<span class="truncate font-medium">{soloStage ?? 'running'}</span>
					{:else}
						<span class="font-medium tabular-nums">{liveScans.count} running</span>
					{/if}
				</span>
				<Spinner class="h-3.5 w-3.5 text-info sm:hidden" />
			{:else if latest}
				<span class="hidden min-w-0 items-center gap-2 sm:flex">
					{#key latest.id}
						<span in:fly={{ y: -6, duration: 220 }} class="flex items-center gap-1.5 min-w-0">
							<span
								class="h-1 w-1 shrink-0 rounded-full {LEVEL_DOT[latest.level] ?? LEVEL_DOT.info}"
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
					class="ml-0.5 inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-chart-1/15 px-1 text-[10px] font-semibold text-chart-1"
				>
					{activityFeed.newCount}
				</span>
			{/if}
		</button>
	{/snippet}
</Hint>
