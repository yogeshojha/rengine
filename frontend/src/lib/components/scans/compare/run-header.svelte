<script lang="ts">
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import ScanStatusBadge from '$lib/components/scan-status-badge.svelte';
	import RunPicker from './run-picker.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { durationText } from '$lib/utilities/scan-status';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import type { ComparableRun, RunSide } from '$lib/types/compare';
	import type { ScanStatus } from '$lib/types/scan';

	interface Props {
		baseline: RunSide;
		current: RunSide;
		runs: ComparableRun[];
		loading: boolean;
		onPick: (side: 'baseline' | 'current', scanId: string) => void;
		onSwap: () => void;
	}

	let { baseline, current, runs, loading, onPick, onSwap }: Props = $props();

	const when = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleString('en-US', {
					month: 'short',
					day: 'numeric',
					hour: 'numeric',
					minute: '2-digit'
				})
			: '';

	const rows = (side: RunSide) => SURFACE_ORDER.reduce((n, s) => n + (side.counts[s.key] ?? 0), 0);
</script>

{#snippet side(run: RunSide, label: string, which: 'baseline' | 'current')}
	<div class="flex min-w-0 flex-col gap-2 px-4 py-3.5 sm:px-5">
		<span class="text-2xs tracking-wider text-muted-foreground uppercase">{label}</span>

		<RunPicker
			{label}
			selected={run.scan_id}
			other={which === 'current' ? baseline.scan_id : current.scan_id}
			{runs}
			{loading}
			onPick={(id) => onPick(which, id)}
		>
			<span class="min-w-0 truncate text-base leading-6 font-semibold">{run.engine_name}</span>
		</RunPicker>

		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
			<span class="tabular-nums">{when(run.started_at)}</span>
			{#if run.duration_seconds != null}
				<span class="opacity-40">·</span>
				<span class="tabular-nums">{durationText(run.duration_seconds)}</span>
			{/if}
			<span class="opacity-40">·</span>
			<ScanStatusBadge status={run.status as ScanStatus} class="h-4 px-1.5 text-2xs" />
		</div>

		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
			<span class="tabular-nums text-foreground">{rows(run).toLocaleString()}</span>
			<span class="text-muted-foreground">rows</span>
			<span class="text-muted-foreground opacity-40">·</span>
			<span class="tabular-nums text-foreground">{run.stages_ran}</span>
			<span class="text-muted-foreground">of {run.stages_planned} stages ran</span>
			{#if run.context_name}
				<span class="text-muted-foreground opacity-40">·</span>
				<span class="text-muted-foreground">{run.context_name}</span>
			{/if}
			<Button
				variant="link"
				size="sm"
				href={ROUTES.scan(run.scan_id)}
				class="ml-auto h-auto gap-1 p-0 text-xs"
			>
				Open run <ArrowUpRight class="size-3" />
			</Button>
		</div>
	</div>
{/snippet}

<div class="relative grid grid-cols-1 sm:grid-cols-2">
	<div class="border-b sm:border-b-0 sm:border-r">
		{@render side(baseline, 'Baseline', 'baseline')}
	</div>
	<div>
		{@render side(current, 'Current', 'current')}
	</div>

	<div
		class="pointer-events-none absolute inset-0 hidden items-center justify-center sm:flex"
		aria-hidden="true"
	>
		<Hint text="Swap the two runs">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon-sm"
					onclick={() => onSwap()}
					aria-hidden="false"
					aria-label="Swap the two runs"
					class="pointer-events-auto size-7 rounded-full bg-background shadow-sm"
				>
					<ArrowLeftRight class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
	</div>
</div>
