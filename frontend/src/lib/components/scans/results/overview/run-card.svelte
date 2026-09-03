<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Circle from '@lucide/svelte/icons/circle';
	import Ban from '@lucide/svelte/icons/ban';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import {
		durationLabel,
		durationText,
		formatSeconds,
		isLiveStatus
	} from '$lib/utilities/scan-status';
	import { plannedStages, stageRows } from '$lib/utilities/scan-progress';
	import type { ScanActivityRead, ScanRead } from '$lib/types/scan';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';

	interface Props {
		scan: ScanRead;
		run: LiveRun | undefined;
		catalog: StageCatalogEntry[];
		activities: ScanActivityRead[];
		now: number;
		onPipeline: () => void;
	}

	let { scan, run, catalog, activities, now, onPipeline }: Props = $props();

	let live = $derived(isLiveStatus(scan.status));
	let planned = $derived(plannedStages(scan, catalog));
	let rows = $derived(stageRows(planned, activities, run));
	let done = $derived(rows.filter((r) => r.state === 'done').length);
	let stopped = $derived(
		new Set(activities.filter((a) => a.status === 'aborted').map((a) => a.name))
	);
	let nextName = $derived(live ? (rows.find((r) => r.state === 'pending')?.name ?? null) : null);
	let runningSince = $derived.by(() => {
		const a = activities.find((x) => x.status === 'running');
		return a?.started_at ? Math.max(0, (now - new Date(a.started_at).getTime()) / 1000) : null;
	});
	let failedRow = $derived(rows.find((r) => r.state === 'failed' && !stopped.has(r.name)));
	let subtitle = $derived.by(() => {
		const dur = durationLabel(scan, now);
		switch (scan.status) {
			case 'pending':
				return `${rows.length} stages queued`;
			case 'running':
				return `${done} of ${rows.length} stages completed · ${dur} elapsed`;
			case 'failed':
				return failedRow ? `Failed at ${failedRow.title} after ${dur}` : `Failed after ${dur}`;
			case 'cancelled':
				return `Stopped after ${done} of ${rows.length} stages · ${dur}`;
			default:
				return `All ${rows.length} stages completed in ${dur}`;
		}
	});
</script>

<Card.Root>
	<Card.Header>
		<Card.Title>Scan stages</Card.Title>
		<Card.Description>{subtitle}</Card.Description>
	</Card.Header>
	<Card.Content>
		{#if !catalog.length}
			<div class="flex flex-col gap-2.5">
				<Skeleton class="h-5 w-3/4" />
				<Skeleton class="h-5 w-2/3" />
				<Skeleton class="h-5 w-1/2" />
			</div>
		{:else}
			<ol class="flex flex-col">
				{#each rows as r (r.name)}
					<li class="flex items-center gap-3 py-1.5">
						{#if r.state === 'done'}
							<CircleCheck class="size-4 shrink-0 text-success" />
						{:else if r.state === 'failed' && stopped.has(r.name)}
							<Ban class="size-4 shrink-0 text-warning" />
						{:else if r.state === 'failed'}
							<CircleX class="size-4 shrink-0 text-destructive" />
						{:else if r.state === 'running'}
							<Spinner class="size-4 shrink-0 text-info" />
						{:else}
							<Circle class="size-4 shrink-0 text-muted-foreground/40" />
						{/if}
						<span
							class="min-w-0 flex-1 truncate text-sm {r.state === 'pending'
								? 'text-muted-foreground'
								: ''}"
						>
							{r.title}
						</span>
						{#if r.state === 'running'}
							<span class="font-mono text-xs text-info tabular-nums">
								{runningSince != null ? formatSeconds(runningSince) : 'running'}
							</span>
						{:else if r.state === 'pending'}
							{#if r.name === nextName}
								<Badge variant="info" class="h-5 px-1.5 text-[10px] font-normal">Next</Badge>
							{:else if !live}
								<span class="text-xs text-muted-foreground">Did not run</span>
							{/if}
						{:else if r.state === 'failed' && stopped.has(r.name)}
							<span class="text-xs text-warning">Stopped</span>
						{:else if r.state === 'failed'}
							<span class="text-xs text-destructive">Failed</span>
						{:else}
							<span class="font-mono text-xs text-muted-foreground tabular-nums">
								{durationText(r.duration)}
							</span>
						{/if}
					</li>
				{/each}
			</ol>
		{/if}
	</Card.Content>
	<Card.Footer>
		<Button variant="link" size="sm" class="h-auto gap-1 px-0" onclick={onPipeline}>
			View pipeline log <ChevronRight class="size-3.5" />
		</Button>
	</Card.Footer>
</Card.Root>
