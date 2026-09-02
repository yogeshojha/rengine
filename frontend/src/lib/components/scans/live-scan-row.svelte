<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Clock from '@lucide/svelte/icons/clock';
	import { ROUTES } from '$lib/config/routes';
	import { elapsedSeconds, formatSeconds } from '$lib/utilities/scan-status';
	import type { ScanRead } from '$lib/types/scan';
	import type { LiveStage } from '$lib/stores/live-scans.svelte';

	interface Props {
		scan: ScanRead;
		stage?: LiveStage;
		now: number;
		onNavigate?: () => void;
	}

	let { scan, stage, now, onNavigate }: Props = $props();

	let queued = $derived(scan.status === 'pending');
	let elapsed = $derived.by(() => {
		const s = elapsedSeconds(scan, now);
		return s == null ? null : formatSeconds(s);
	});
	let detail = $derived(queued ? 'Queued' : (stage?.title ?? scan.engine_name));
</script>

<a
	href={ROUTES.scan(scan.id)}
	onclick={onNavigate}
	title="{scan.execution_config.target_value} · {scan.engine_name}"
	class="flex items-center gap-2 rounded-md px-1.5 py-1 transition-colors hover:bg-accent/60"
>
	{#if queued}
		<Clock class="size-3 shrink-0 text-muted-foreground" />
	{:else}
		<Spinner class="size-3 shrink-0 text-info" />
	{/if}
	<div class="min-w-0 flex-1 leading-tight">
		<p class="truncate font-mono text-[11px] text-foreground">
			{scan.execution_config.target_value}
		</p>
		<p class="truncate text-[10px] text-muted-foreground">{detail}</p>
	</div>
	{#if elapsed}
		<span class="shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground">{elapsed}</span>
	{/if}
</a>
