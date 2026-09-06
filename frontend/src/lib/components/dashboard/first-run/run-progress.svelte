<script lang="ts">
	import { untrack } from 'svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Check from '@lucide/svelte/icons/check';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import type { DashboardOverview } from '$lib/types/dashboard';
	import { formatSeconds } from '$lib/utilities/scan-status';
	import { plannedStages, stageProgress } from '$lib/utilities/scan-progress';

	interface Props {
		overview: DashboardOverview | null;
		now: number;
	}

	let { overview, now }: Props = $props();

	let scan = $derived(liveScans.scans[0] ?? null);
	let run = $derived(scan ? liveScans.runFor(scan.id) : undefined);
	let planned = $derived(scan ? plannedStages(scan, engineCatalogStore.stages) : []);
	let produced = $derived(new Set(planned.flatMap((s) => s.produces)));
	let progress = $derived(scan ? stageProgress(scan, run, planned) : null);
	let rows = $derived(progress?.steps ?? []);
	let elapsed = $derived.by(() => {
		if (!scan?.started_at) return null;
		return Math.max(0, Math.floor((now - new Date(scan.started_at).getTime()) / 1000));
	});
	let headline = $derived.by(() => {
		if (!progress) return '';
		const parts = [progress.label];
		if (progress.total) parts.push(`${progress.done} of ${progress.total} stages done`);
		if (elapsed !== null) parts.push(`running ${formatSeconds(elapsed)}`);
		return parts.join(' · ');
	});
	let surface = $derived(overview?.surface ?? []);

	// every SSE message recomputes progress, so the counts refetch only when a stage lands
	let counted = -1;
	$effect(() => {
		const landed = progress?.done ?? 0;
		untrack(() => {
			if (landed === counted) return;
			counted = landed;
			if (landed > 0) dashboardStore.refresh();
		});
	});
</script>

{#if scan}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="flex flex-wrap items-start gap-x-4 gap-y-3 px-5 py-5">
			<div class="flex min-w-[16rem] flex-1 flex-col gap-1">
				<h2 class="flex items-center gap-2.5 text-xl font-semibold tracking-tight sm:text-2xl">
					<span class="flex h-8 shrink-0 items-center">
						<Spinner class="size-4 text-info" />
					</span>
					<span>
						Scanning
						<span class="font-mono text-lg sm:text-xl">{scan.execution_config.target_value}</span>
					</span>
				</h2>
				<p class="text-sm text-muted-foreground">{headline}</p>
			</div>
			<Button variant="outline" size="sm" href={ROUTES.scan(scan.id)}>
				Open scan
				<ArrowUpRight class="size-4" />
			</Button>
		</div>

		<div class="grid grid-cols-2 border-t sm:grid-cols-3 lg:grid-cols-5">
			{#each SURFACE_ORDER as spec (spec.key)}
				{@const metric = surface.find((m) => m.key === spec.key)}
				{@const seen = metric && metric.targets_covered > 0}
				{@const inPlan = spec.kinds.some((k) => produced.has(k))}
				{@const Icon = spec.icon}
				<div class="flex min-w-0 flex-col gap-1.5 border-t border-l px-5 py-4 first:border-l-0">
					<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
						<Icon class="size-3.5" />
						{spec.label}
					</span>
					<span
						class="text-2xl leading-none font-semibold tracking-tight tabular-nums {seen
							? ''
							: 'font-medium text-muted-foreground'}"
					>
						{seen ? (metric?.value ?? 0).toLocaleString() : '—'}
					</span>
					<span class="text-xs text-muted-foreground">
						{seen ? 'so far' : inPlan ? 'queued' : 'not in plan'}
					</span>
				</div>
			{/each}
		</div>

		{#if rows.length}
			<div class="flex flex-wrap gap-1.5 border-t px-5 py-4">
				{#each rows as row (row.name)}
					<span
						class="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs {row.state ===
						'done'
							? 'border-success/35 text-success'
							: row.state === 'running'
								? 'border-info/40 bg-info/5'
								: 'border-dashed text-muted-foreground'}"
					>
						{#if row.state === 'done'}
							<Check class="size-3" />
						{:else if row.state === 'running'}
							<Spinner class="size-3 text-info" />
						{/if}
						{row.title}
					</span>
				{/each}
			</div>
		{/if}
	</Card.Root>
{/if}
