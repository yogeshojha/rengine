<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { scansApi } from '$lib/api/scans';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import {
		ACTIVITY_STATUS_LABEL,
		activityStatusClass,
		durationText,
		isOpenStatus
	} from '$lib/utilities/scan-status';
	import type { ScanActivityRead, ScanRead } from '$lib/types/scan';

	interface Props {
		projectId: string;
		scan: ScanRead;
		now: number;
	}

	let { projectId, scan, now }: Props = $props();

	let activities = $state<ScanActivityRead[] | null>(null);
	let error = $state<string | null>(null);
	let attempt = $state(0);
	let open = $derived(isOpenStatus(scan.status));
	let tick = $derived(open ? Math.floor(now / 5000) : 0);

	$effect(() => {
		void tick;
		void attempt;
		const id = scan.id;
		scansApi
			.activities(id, projectId)
			.then((a) => {
				activities = a;
				error = null;
			})
			.catch((e) => (error = e instanceof Error ? e.message : 'Stages not loaded.'));
	});

	function retry() {
		error = null;
		attempt++;
	}

	let t0 = $derived(new Date(scan.started_at ?? scan.created_at).getTime());
	let t1 = $derived(
		scan.completed_at && !open ? new Date(scan.completed_at).getTime() : Math.max(now, t0 + 1000)
	);
	let span = $derived(Math.max(1, t1 - t0));
	let rows = $derived(
		(activities ?? [])
			.filter((a) => a.status !== 'skipped' || a.error)
			.map((a) => {
				const s = a.started_at ? new Date(a.started_at).getTime() : null;
				const e = a.completed_at
					? new Date(a.completed_at).getTime()
					: a.status === 'running'
						? now
						: null;
				return {
					a,
					left: s == null ? 0 : ((s - t0) / span) * 100,
					width: s == null || e == null ? 0 : Math.max(((e - s) / span) * 100, 0.6),
					note:
						a.error ??
						(a.status === 'partial' || a.status === 'failed'
							? ((a.result?.reason as string | undefined) ?? null)
							: null)
				};
			})
	);
	let skipped = $derived(
		(activities ?? []).filter((a) => a.status === 'skipped' && !a.error).length
	);
	let short = $derived(
		rows.filter((r) => r.a.status === 'partial' || r.a.status === 'failed').length
	);
	let run = $derived(liveScans.runFor(scan.id));

	const BAR: Record<string, string> = {
		success: 'bg-series',
		partial: 'bg-warning',
		failed: 'bg-destructive',
		aborted: 'bg-muted-foreground/50',
		running: 'bg-info',
		paused: 'bg-muted-foreground/40',
		pending: 'bg-muted-foreground/20'
	};
</script>

{#if error}
	<div class="flex items-center gap-3 px-1 py-6 text-sm text-muted-foreground">
		<span>{error}</span>
		<button type="button" class="text-primary hover:text-primary/80" onclick={() => retry()}>
			Retry
		</button>
	</div>
{:else if !activities}
	<div class="space-y-1.5 py-3">
		{#each { length: 6 } as _, i (i)}
			<Skeleton class="h-5 rounded" />
		{/each}
	</div>
{:else if rows.length === 0}
	<p class="px-1 py-6 text-sm text-muted-foreground">No stage has started.</p>
{:else}
	<div class="flex flex-col gap-2 py-2">
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-xs text-muted-foreground">
			<span
				><span class="font-mono text-foreground"
					>{rows.filter((r) => r.a.status === 'success').length}</span
				> completed</span
			>
			{#if short}<span><span class="font-mono text-warning">{short}</span> partial or failed</span
				>{/if}
			{#if skipped}<span><span class="font-mono">{skipped}</span> skipped</span>{/if}
			{#if run?.message}<span class="truncate">{run.message}</span>{/if}
		</div>
		<ul class="flex flex-col">
			{#each rows as r (r.a.id)}
				<li
					class="grid grid-cols-[minmax(0,11rem)_minmax(0,1fr)_4rem] items-center gap-3 py-1 text-xs"
				>
					<div class="min-w-0">
						<div class="truncate">{r.a.title}</div>
						{#if r.note}
							<div class="truncate text-2xs {activityStatusClass(r.a.status)}">{r.note}</div>
						{/if}
					</div>
					<div class="relative h-2.5 rounded-sm bg-muted/40">
						<span
							class="absolute inset-y-0 rounded-sm {BAR[r.a.status] ?? 'bg-muted-foreground/30'}"
							style="left: {r.left}%; width: {r.width}%"
						></span>
					</div>
					<div class="text-right font-mono text-2xs tabular-nums {activityStatusClass(r.a.status)}">
						{r.a.status === 'success'
							? durationText(r.a.duration_seconds)
							: ACTIVITY_STATUS_LABEL[r.a.status]}
					</div>
				</li>
			{/each}
		</ul>
	</div>
{/if}
