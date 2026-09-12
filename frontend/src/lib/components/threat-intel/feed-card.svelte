<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Hint from '$lib/components/hint.svelte';
	import { FEED_STATUS_DOT, FEED_STATUS_TONE, FeedStatus } from '$lib/config/threat-intel';
	import { relativeTime } from '$lib/utilities/dates';
	import type { ThreatFeedRead } from '$lib/types/threat-intel';

	interface Props {
		feed: ThreatFeedRead;
	}

	let { feed }: Props = $props();

	let syncing = $derived(feed.status === FeedStatus.SYNCING);
	let mb = $derived(feed.bytes ? `${(feed.bytes / 1e6).toFixed(1)} MB` : '');
	let seconds = $derived(feed.duration_ms ? `${(feed.duration_ms / 1000).toFixed(1)}s` : '');
	let version = $derived(feed.version?.replace('model_version:', '').split(',')[0] ?? '');
</script>

<div class="flex min-w-0 flex-col gap-3 p-5">
	<div class="flex items-start justify-between gap-3">
		<div class="flex min-w-0 flex-col gap-0.5">
			<div class="flex items-center gap-2">
				<span class="flex h-5 shrink-0 items-center">
					<span
						class="size-1.5 rounded-full {FEED_STATUS_DOT[feed.status]} {syncing
							? 'animate-pulse'
							: ''}"
					></span>
				</span>
				<h3 class="text-sm leading-5 font-semibold">{feed.label}</h3>
			</div>
			<p class="text-xs text-muted-foreground">{feed.tagline}</p>
		</div>
		<span class="text-xs whitespace-nowrap {FEED_STATUS_TONE[feed.status]}">
			{feed.status_label}
		</span>
	</div>

	<div class="flex items-baseline gap-2">
		<span class="font-mono text-3xl leading-none font-semibold tabular-nums">
			{feed.rows.toLocaleString()}
		</span>
		<span class="text-xs text-muted-foreground">
			{feed.kind === 'kev' ? 'catalogued CVEs' : 'scored CVEs'}
		</span>
	</div>

	<p class="text-xs leading-relaxed text-muted-foreground">{feed.description}</p>

	{#if feed.error}
		<p class="text-xs text-destructive">{feed.error}</p>
	{/if}

	<div class="flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-3 text-2xs">
		{#if version}
			<Hint text="Version published by {feed.source}">
				{#snippet child(props)}
					<span {...props} class="truncate font-mono text-muted-foreground">{version}</span>
				{/snippet}
			</Hint>
		{/if}
		{#if feed.last_synced_at}
			<span class="text-muted-foreground">{relativeTime(feed.last_synced_at)}</span>
		{/if}
		{#if mb}
			<Hint text="Downloaded {mb} in {seconds}">
				{#snippet child(props)}
					<span {...props} class="text-muted-foreground tabular-nums">{mb}</span>
				{/snippet}
			</Hint>
		{/if}
		<a
			class="ml-auto inline-flex items-center gap-1 text-muted-foreground hover:text-foreground hover:underline"
			href={feed.source_url}
			target="_blank"
			rel="noopener noreferrer"
		>
			{feed.source}
			<ExternalLink class="size-2.5" />
		</a>
	</div>
	<p class="text-2xs text-muted-foreground">{feed.license}</p>
</div>
