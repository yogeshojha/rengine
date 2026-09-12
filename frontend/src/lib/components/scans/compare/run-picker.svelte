<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Check from '@lucide/svelte/icons/check';
	import * as Popover from '$lib/components/ui/popover';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { durationText } from '$lib/utilities/scan-status';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import type { Snippet } from 'svelte';
	import type { ComparableRun } from '$lib/types/compare';

	interface Props {
		label: string;
		selected: string;
		other: string;
		runs: ComparableRun[];
		loading: boolean;
		onPick: (scanId: string) => void;
		children: Snippet;
	}

	let { label, selected, other, runs, loading, onPick, children }: Props = $props();

	let open = $state(false);
	let usable = $derived(
		runs.filter((r) => r.comparable && r.scan_id !== selected && r.scan_id !== other)
	);
	let blocked = $derived(runs.filter((r) => !r.comparable));

	const when = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleString('en-US', {
					month: 'short',
					day: 'numeric',
					hour: 'numeric',
					minute: '2-digit'
				})
			: 'not started';

	function choose(scanId: string) {
		open = false;
		onPick(scanId);
	}
</script>

{#snippet meta(run: ComparableRun)}
	<span class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
		<span class="tabular-nums">{when(run.started_at)}</span>
		{#if run.duration_seconds != null}
			<span class="opacity-40">·</span>
			<span class="tabular-nums">{durationText(run.duration_seconds)}</span>
		{/if}
		<span class="opacity-40">·</span>
		<span class="tabular-nums"
			>{SURFACE_ORDER.reduce((n, s) => n + (run.counts[s.key] ?? 0), 0).toLocaleString()} rows</span
		>
	</span>
{/snippet}

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				type="button"
				class="-mx-1.5 -my-0.5 inline-flex max-w-full items-center gap-1.5 rounded-md px-1.5 py-0.5 text-left transition-colors hover:bg-accent/60 data-[state=open]:bg-accent/60"
				aria-label="Choose the {label.toLowerCase()} run"
			>
				{@render children()}
				<ChevronDown class="size-3.5 shrink-0 text-muted-foreground" />
			</button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content align="start" class="w-[26rem] max-w-[calc(100vw-2rem)] p-0">
		<PanelHead title="Choose the {label.toLowerCase()} run" description="Runs of this target" />
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[22rem]">
			<div class="flex flex-col p-1.5">
				{#if loading}
					{#each [0, 1, 2] as i (i)}
						<Skeleton class="m-1 h-11" />
					{/each}
				{:else if !usable.length && !blocked.length}
					<p class="px-3 py-4 text-sm text-muted-foreground">No other finished runs.</p>
				{/if}

				{#each usable as run (run.scan_id)}
					<button
						type="button"
						onclick={() => choose(run.scan_id)}
						class="flex flex-col gap-0.5 rounded-md px-2.5 py-2 text-left transition-colors hover:bg-accent/60"
					>
						<span class="flex items-center gap-2 text-sm leading-5 font-medium">
							{run.engine_name}
							{#if run.scan_id === selected}
								<Check class="size-3.5 text-primary" />
							{/if}
						</span>
						{@render meta(run)}
					</button>
				{/each}

				{#if blocked.length}
					<p class="px-2.5 pt-3 pb-1 text-2xs text-muted-foreground">Cannot be compared</p>
					{#each blocked as run (run.scan_id)}
						<div class="flex flex-col gap-0.5 px-2.5 py-2 opacity-60">
							<span class="text-sm leading-5 font-medium">{run.engine_name}</span>
							{@render meta(run)}
							<span class="text-xs text-muted-foreground">{run.reason}</span>
						</div>
					{/each}
				{/if}
			</div>
		</ScrollArea>
	</Popover.Content>
</Popover.Root>
