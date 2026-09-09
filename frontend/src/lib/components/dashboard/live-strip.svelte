<script lang="ts">
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';

	const MAX = 4;
	let scans = $derived(liveScans.scans.slice(0, MAX));
	let more = $derived(Math.max(0, liveScans.scans.length - MAX));
</script>

{#if scans.length}
	<div class="flex flex-wrap items-center gap-2 text-xs">
		<span class="flex items-center gap-1.5 text-muted-foreground">
			<span class="relative flex size-2">
				<span class="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-60"
				></span>
				<span class="relative inline-flex size-2 rounded-full bg-info"></span>
			</span>
			{liveScans.scans.length === 1 ? 'Scanning' : `${liveScans.scans.length} scans running`}
		</span>
		{#each scans as s (s.id)}
			{@const run = liveScans.runFor(s.id)}
			<a
				href={ROUTES.scan(s.id)}
				class="flex items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 hover:bg-muted/50"
			>
				<span class="font-mono">{s.execution_config.target_value}</span>
				{#if run?.stage}
					<span class="text-muted-foreground">· {run.stage.title}</span>
				{/if}
				{#if s.started_at}
					<span class="text-muted-foreground">· {relativeTime(s.started_at)}</span>
				{/if}
			</a>
		{/each}
		{#if more > 0}
			<a href={ROUTES.scans} class="text-muted-foreground hover:underline">+{more} more</a>
		{/if}
	</div>
{/if}
