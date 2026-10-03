<script lang="ts">
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import ScanStatusBadge from '$lib/components/scan-status-badge.svelte';
	import RunPicker from './run-picker.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { durationText } from '$lib/utilities/scan-status';
	import { formatDateTime } from '$lib/utilities/dates';
	import { runRows, type ComparableRun, type RunSide } from '$lib/types/compare';
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
</script>

{#snippet side(run: RunSide, label: string, which: 'baseline' | 'current')}
	<div class="flex min-w-0 flex-col gap-2 px-4 py-3.5 sm:px-5">
		<div class="flex items-center justify-between gap-2">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">{label}</span>
			{#if which === 'current'}
				<Button
					variant="ghost"
					size="icon"
					class="-my-1.5 size-7 sm:hidden"
					aria-label="Swap runs"
					onclick={() => onSwap()}
				>
					<ArrowUpDown class="size-3.5" />
				</Button>
			{/if}
		</div>

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
			<span class="tabular-nums">{run.started_at ? formatDateTime(run.started_at) : ''}</span>
			{#if run.duration_seconds != null}
				<span class="opacity-40">·</span>
				<span class="tabular-nums">{durationText(run.duration_seconds)}</span>
			{/if}
			<span class="opacity-40">·</span>
			<ScanStatusBadge status={run.status as ScanStatus} class="h-4 px-1.5 text-2xs" />
		</div>

		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
			<span class="tabular-nums text-foreground">{runRows(run.counts).toLocaleString()}</span>
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
				class="ml-auto h-auto p-0 text-xs"
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

	<div class="pointer-events-none absolute inset-0 hidden items-center justify-center sm:flex">
		<Hint text="Swap runs">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon-sm"
					onclick={() => onSwap()}
					aria-label="Swap runs"
					class="pointer-events-auto rounded-full bg-background shadow-sm"
				>
					<ArrowLeftRight class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
	</div>
</div>
