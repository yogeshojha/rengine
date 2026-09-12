<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import GitCompareArrows from '@lucide/svelte/icons/git-compare-arrows';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { durationText } from '$lib/utilities/scan-status';
	import type { ComparableRun } from '$lib/types/compare';

	interface Props {
		reason: string;
		currentId: string;
		runs: ComparableRun[];
		loading: boolean;
	}

	let { reason, currentId, runs, loading }: Props = $props();

	let usable = $derived(runs.filter((r) => r.comparable));
	let blocked = $derived(runs.filter((r) => !r.comparable));

	const when = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleString('en-US', {
					month: 'short',
					day: 'numeric',
					hour: 'numeric',
					minute: '2-digit'
				})
			: '';
	const rows = (run: ComparableRun) =>
		SURFACE_ORDER.reduce((n, s) => n + (run.counts[s.key] ?? 0), 0);
</script>

<div class="flex flex-col gap-4 p-4 sm:p-5">
	<div class="flex gap-3 rounded-lg border border-warning/40 bg-warning/5 p-4">
		<TriangleAlert class="mt-0.5 size-4 shrink-0 text-warning" />
		<div class="flex min-w-0 flex-col gap-1">
			<p class="text-sm font-semibold">These two runs cannot be compared</p>
			<p class="text-sm text-muted-foreground">{reason}</p>
		</div>
	</div>

	<div class="overflow-hidden rounded-lg border">
		<PanelHead
			title="Runs of this target"
			description="Pick one to compare with the run you opened"
		/>
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[26rem]">
			<div class="flex flex-col">
				{#if loading}
					{#each [0, 1, 2] as i (i)}
						<Skeleton class="m-2 h-12" />
					{/each}
				{:else if !usable.length && !blocked.length}
					<p class="px-5 py-6 text-sm text-muted-foreground">
						This target has no other finished run.
					</p>
				{/if}

				{#each usable as run (run.scan_id)}
					<a
						href={ROUTES.compare(currentId, run.scan_id)}
						class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-5 py-3 transition-colors last:border-b-0 hover:bg-accent/40"
					>
						<GitCompareArrows class="size-3.5 shrink-0 text-muted-foreground" />
						<span class="text-sm font-medium">{run.engine_name}</span>
						<span class="text-xs text-muted-foreground tabular-nums">
							{[
								when(run.started_at),
								run.duration_seconds != null ? durationText(run.duration_seconds) : ''
							]
								.filter(Boolean)
								.join(' · ')}
						</span>
						<span class="ml-auto text-xs text-muted-foreground tabular-nums">
							{rows(run).toLocaleString()} rows
						</span>
					</a>
				{/each}

				{#each blocked as run (run.scan_id)}
					<div
						class="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-5 py-3 opacity-60 last:border-b-0"
					>
						<span class="text-sm font-medium">{run.engine_name}</span>
						<span class="text-xs text-muted-foreground tabular-nums">
							{when(run.started_at)}
						</span>
						<span class="w-full text-xs text-muted-foreground">{run.reason}</span>
					</div>
				{/each}
			</div>
		</ScrollArea>
	</div>

	<div class="flex flex-wrap gap-2">
		<Button variant="outline" size="sm" href={ROUTES.scan(currentId)} class="gap-1.5">
			Open the run <ArrowUpRight class="size-3.5" />
		</Button>
		<Button variant="ghost" size="sm" href={ROUTES.scans}>All scans</Button>
	</div>
</div>
