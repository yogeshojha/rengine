<script lang="ts">
	import { untrack } from 'svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import SectionHead from '$lib/components/section-head.svelte';
	import { tripwiresApi } from '$lib/api/tripwires';
	import { CheckStatus, RECENT_DAYS, dimensionSpec } from '$lib/config/tripwires';
	import type { TripwireBacktest, TripwirePreviewRequest } from '$lib/types/tripwire';
	import { formatShortDate } from '$lib/utilities/dates';

	interface Props {
		projectId: string;
		request: TripwirePreviewRequest;
		enabled?: boolean;
	}

	let { projectId, request, enabled = true }: Props = $props();

	const DEBOUNCE_MS = 400;
	const SHOWN_RUNS = 6;

	let backtest = $state<TripwireBacktest | null>(null);
	let loading = $state(false);
	let failure = $state<string | null>(null);
	let seq = 0;

	let spec = $derived(dimensionSpec(request.dimension));
	let signature = $derived(JSON.stringify(request));
	let fired = $derived(backtest?.runs.filter((r) => r.status === CheckStatus.Fired) ?? []);
	let bars = $derived(backtest ? [...backtest.runs].reverse() : []);
	let peak = $derived(Math.max(1, ...bars.map((r) => r.fired)));
	let noun = $derived((n: number) => (n === 1 ? spec.noun : spec.nounPlural));

	$effect(() => {
		void signature;
		const on = enabled;
		untrack(() => {
			if (!on) {
				backtest = null;
				failure = null;
				return;
			}
			const mine = ++seq;
			loading = true;
			const timer = setTimeout(async () => {
				try {
					const result = await tripwiresApi.backtest(projectId, request);
					if (mine !== seq) return;
					backtest = result;
					failure = null;
				} catch (e) {
					if (mine !== seq) return;
					backtest = null;
					failure = e instanceof Error ? e.message : 'Backtest not loaded';
				} finally {
					if (mine === seq) loading = false;
				}
			}, DEBOUNCE_MS);
			return () => clearTimeout(timer);
		});
	});
</script>

<div class="flex flex-col gap-3 rounded-lg border bg-muted/20 p-4">
	<SectionHead title="Last {backtest?.days ?? RECENT_DAYS} days" />
	{#if !enabled}
		<p class="text-xs text-muted-foreground">Not evaluated until the query is valid.</p>
	{:else if loading && !backtest}
		<Skeleton class="h-4 w-40" />
		<Skeleton class="h-12 w-full" />
	{:else if backtest?.error}
		<p class="text-xs text-destructive">{backtest.error.message}</p>
	{:else if failure}
		<p class="text-xs text-destructive">{failure}</p>
	{:else if backtest}
		<p class="text-sm">
			<span class="font-semibold tabular-nums">{fired.length}</span>
			<span class="text-muted-foreground">
				{fired.length === 1 ? 'firing' : 'firings'} across {backtest.runs.length}
				{backtest.runs.length === 1 ? 'run' : 'runs'}{backtest.capped ? ' shown' : ''}
			</span>
		</p>
		{#if bars.length > 0}
			<div class="flex h-12 items-end gap-0.5 border-b" role="img" aria-label="Rows fired per run">
				{#each bars as run (run.scan_id)}
					<div
						class="flex-1 rounded-t-sm {run.fired ? 'bg-series' : 'bg-muted'}"
						style="height:{run.fired ? Math.max(12, Math.round((run.fired / peak) * 100)) : 4}%"
					></div>
				{/each}
			</div>
			<div class="flex flex-col divide-y divide-border/60">
				{#each fired.slice(0, SHOWN_RUNS) as run (run.scan_id)}
					<div class="grid grid-cols-[72px_minmax(0,1fr)_auto] items-center gap-2 py-1.5 text-2xs">
						<span class="text-muted-foreground"
							>{run.completed_at ? formatShortDate(run.completed_at) : ''}</span
						>
						<span class="truncate font-mono">{run.target_value}</span>
						<span class="tabular-nums">{run.fired.toLocaleString()} {noun(run.fired)}</span>
					</div>
				{/each}
			</div>
		{:else}
			<p class="text-xs text-muted-foreground">No settled run in the window.</p>
		{/if}
	{/if}
</div>
