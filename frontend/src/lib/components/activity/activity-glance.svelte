<script lang="ts">
	import { activityFeed } from '$lib/stores/activity-feed.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { ACTIVITY_KINDS } from '$lib/config/activity';
	import { activityLead } from '$lib/utilities/activity';
	import { relativeTime } from '$lib/utilities/dates';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import Activity from '@lucide/svelte/icons/activity';
	import Clock from '@lucide/svelte/icons/clock';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';

	let solo = $derived(liveScans.count === 1 ? liveScans.scans[0] : null);
	let stage = $derived(solo ? liveScans.runFor(solo.id)?.stage?.title : null);
	let failure = $derived(activityFeed.failure);
	let failureKind = $derived(failure ? ACTIVITY_KINDS[failure.event_type] : null);
	let failureTime = $derived.by(() => {
		void activityFeed.tick;
		return failure ? relativeTime(failure.timestamp) : '';
	});
	let quiet = $derived(!sseStore.isReconnecting && !liveScans.hasLive && !failure);
</script>

<Hint text="Activity">
	{#snippet child(props)}
		<button
			{...props}
			type="button"
			aria-label="Activity"
			aria-expanded={activityFeed.open}
			data-activity-glance
			onclick={() => activityFeed.toggle()}
			class={quiet
				? 'inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground'
				: `inline-flex h-8 max-w-80 items-center gap-2 rounded-full border bg-muted/40 px-3 text-xs transition-colors hover:bg-muted ${activityFeed.open ? 'ring-1 ring-primary/30' : ''}`}
		>
			{#if sseStore.isReconnecting}
				<span class="size-1.5 shrink-0 rounded-full bg-warning"></span>
				<span class="font-medium text-warning">Reconnecting</span>
			{:else if solo}
				{#if solo.status === 'pending'}
					<Clock class="size-3.5 shrink-0 text-muted-foreground" />
				{:else}
					<Spinner class="size-3 shrink-0 text-info" />
				{/if}
				<span class="max-w-36 truncate font-mono text-foreground">
					{solo.execution_config.target_value}
				</span>
				<span
					class="truncate {solo.status === 'pending'
						? 'text-muted-foreground'
						: 'font-medium text-info'}"
				>
					{solo.status === 'pending'
						? SCAN_STATUS_LABEL.pending
						: (stage ?? SCAN_STATUS_LABEL[solo.status] ?? 'Starting')}
				</span>
			{:else if liveScans.hasLive}
				<Spinner class="size-3 shrink-0 text-info" />
				<span class="font-medium text-info tabular-nums">{liveScans.summary}</span>
			{:else if failure && failureKind}
				<span class="size-1.5 shrink-0 rounded-full bg-destructive"></span>
				<span
					class="max-w-40 truncate {failureKind.byTarget && failure.target_value
						? 'font-mono'
						: ''} text-foreground"
				>
					{activityLead(failure)}
				</span>
				{#if failureKind.run}
					<span class="font-medium text-destructive">
						{SCAN_STATUS_LABEL[failureKind.run].toLowerCase()}
					</span>
				{/if}
				<span class="shrink-0 font-mono text-2xs text-muted-foreground tabular-nums">
					{failureTime}
				</span>
			{:else}
				<Activity class="size-4" />
			{/if}
		</button>
	{/snippet}
</Hint>
