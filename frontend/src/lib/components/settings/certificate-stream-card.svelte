<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import SectionHead from '$lib/components/section-head.svelte';
	import { watchesApi } from '$lib/api/watches';
	import { STREAM_POLL_MS } from '$lib/config/watch';
	import { relativeTime } from '$lib/utilities/dates';
	import type { StreamStatus } from '$lib/types/watch';

	let stream = $state<StreamStatus | null>(null);
	let failed = $state(false);
	let timer: ReturnType<typeof setInterval> | null = null;

	async function load() {
		try {
			stream = await watchesApi.stream();
			failed = false;
		} catch {
			failed = true;
		}
	}

	$effect(() => {
		void load();
		timer = setInterval(() => void load(), STREAM_POLL_MS);
		return () => {
			if (timer) clearInterval(timer);
		};
	});

	const version = $derived(
		stream?.version?.replace(/^certspotter version /, 'certspotter ').split(' (')[0]
	);
	const streamState = $derived.by(() => {
		if (failed || !stream) return { label: 'Status not read', tone: 'text-muted-foreground' };
		if (!stream.reachable) return { label: 'Not running', tone: 'text-destructive' };
		if (stream.running) return { label: 'Connected', tone: 'text-success' };
		return { label: 'Idle', tone: 'text-muted-foreground' };
	});
</script>

<Card.Root class="gap-0 py-0">
	<div class="border-b p-4">
		<SectionHead title="Certificate stream" count={version}>
			<span>Certificate transparency for the watched apexes</span>
		</SectionHead>
	</div>
	<div class="grid grid-cols-2 gap-px bg-border sm:grid-cols-4">
		<div class="flex flex-col gap-0.5 bg-card px-4 py-3">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">Stream</span>
			<span class="text-sm font-medium {streamState.tone}">{streamState.label}</span>
		</div>
		<div class="flex flex-col gap-0.5 bg-card px-4 py-3">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">Watched apexes</span>
			<span class="text-sm font-medium tabular-nums">{stream?.items ?? 0}</span>
		</div>
		<div class="flex flex-col gap-0.5 bg-card px-4 py-3">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">Last certificate</span>
			<span class="text-sm font-medium">
				{stream?.last_certificate_at ? relativeTime(stream.last_certificate_at) : 'None yet'}
			</span>
		</div>
		<div class="flex flex-col gap-0.5 bg-card px-4 py-3">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">Since start</span>
			<span class="text-sm font-medium tabular-nums">
				{stream?.certificates_seen ?? 0}
				{(stream?.certificates_seen ?? 0) === 1 ? 'certificate' : 'certificates'}
				{#if stream?.started_at}
					<span class="text-xs font-normal text-muted-foreground">
						· {relativeTime(stream.started_at)}
					</span>
				{/if}
			</span>
		</div>
	</div>
	{#if stream?.last_error}
		<div class="border-t px-4 py-2.5 text-xs text-destructive">
			{stream.last_error}
			{#if stream.last_error_at}
				<span class="text-muted-foreground">· {relativeTime(stream.last_error_at)}</span>
			{/if}
		</div>
	{:else if failed}
		<div class="border-t px-4 py-2.5 text-xs text-muted-foreground">
			The API did not respond. Check that the api service is running.
		</div>
	{:else if stream && !stream.reachable}
		<div class="border-t px-4 py-2.5 text-xs text-muted-foreground">
			The ct-stream service has not reported. Check that it is running.
		</div>
	{/if}
</Card.Root>
