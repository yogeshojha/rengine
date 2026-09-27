<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import ScanStatusBadge from '$lib/components/scan-status-badge.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { isOpenStatus } from '$lib/utilities/scan-status';
	import { plannedStages, stageProgress } from '$lib/utilities/scan-progress';
	import { queueLabel } from '$lib/config/scan-admission';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		scan: ScanRead;
	}

	let { scan }: Props = $props();

	let open = $derived(isOpenStatus(scan.status));
	let progress = $derived(
		open
			? stageProgress(
					scan,
					liveScans.runFor(scan.id),
					plannedStages(scan, engineCatalogStore.stages)
				)
			: null
	);
	let ended = $derived(scan.status === 'failed' || scan.status === 'cancelled');
</script>

<div class="flex min-w-0 flex-col gap-1">
	<ScanStatusBadge status={scan.status} class="w-fit" />
	{#if progress && scan.status !== 'pending'}
		<div class="flex items-center gap-1.5">
			<div
				class="h-1 w-16 overflow-hidden rounded-full bg-muted"
				role="progressbar"
				aria-valuenow={progress.percent}
				aria-valuemin={0}
				aria-valuemax={100}
				aria-label="Stages done"
			>
				<div
					class="h-full rounded-full {scan.status === 'paused'
						? 'bg-muted-foreground/50'
						: 'bg-info'}"
					style="width: {Math.max(progress.percent, 4)}%"
				></div>
			</div>
			<span class="font-mono text-2xs text-muted-foreground tabular-nums"
				>{progress.done}/{progress.total}</span
			>
		</div>
		<span class="truncate text-2xs text-muted-foreground"
			>{scan.status === 'paused' ? 'Paused' : progress.label}</span
		>
	{:else if scan.status === 'pending' && scan.queue_position != null}
		<span class="text-2xs text-muted-foreground">{queueLabel(scan.queue_position)}</span>
	{:else if ended && scan.error}
		<Hint text={scan.error}>
			{#snippet child(props)}
				<span {...props} class="line-clamp-1 max-w-[140px] text-2xs text-destructive"
					>{scan.error}</span
				>
			{/snippet}
		</Hint>
	{/if}
</div>
