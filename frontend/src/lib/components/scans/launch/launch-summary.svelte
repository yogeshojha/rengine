<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import FootprintMeter from '$lib/components/engines/footprint-meter.svelte';
	import type { ScanPreview } from '$lib/types/scan';
	import WhatRuns from './what-runs.svelte';
	import type { LaunchState } from './launch-state.svelte';

	interface Props {
		launch: LaunchState;
		preview: ScanPreview | null;
		previewLoading?: boolean;
		open: boolean;
	}

	let { launch, preview, previewLoading = false, open = $bindable(false) }: Props = $props();

	let count = $derived(launch.runningStages.length);
	let impliedTitles = $derived(
		launch.mode === 'quick'
			? launch.runningStages
					.filter((s) => launch.resolution?.implied.has(s.name))
					.map((s) => s.title)
			: []
	);
	let notes = $derived.by(() => {
		if (!impliedTitles.length) return [] as string[];
		return [`Included automatically: ${impliedTitles.join(', ')}.`];
	});
</script>

<Collapsible.Root bind:open class="flex flex-col">
	<div class="flex min-h-7 flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
		{#if launch.summary}
			<span class="font-semibold tabular-nums">{count} {count === 1 ? 'stage' : 'stages'}</span>
			<span class="text-muted-foreground">·</span>
			<FootprintMeter
				footprint={launch.summary.footprint}
				requestsPerSecond={launch.summary.requestsPerSecond}
				class="text-[13px]"
			/>
			{#if preview?.summary.estimated_duration_seconds}
				<span class="text-muted-foreground">·</span>
				<span>Estimated {preview.summary.estimated_duration_human}</span>
			{:else if previewLoading}
				<span class="text-muted-foreground">·</span>
				<Skeleton class="h-3.5 w-16" />
			{/if}
		{:else}
			<Skeleton class="h-4 w-48" />
		{/if}
		<span class="flex-1"></span>
		{#if launch.mode === 'quick'}
			<Collapsible.Trigger
				class="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[13px] font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
			>
				Execution plan
				<ChevronRight class="size-3.5 transition-transform {open ? 'rotate-90' : ''}" />
			</Collapsible.Trigger>
		{/if}
	</div>
	<Collapsible.Content class="flex flex-col gap-2 pt-2">
		<WhatRuns stages={launch.runningStages} implied={launch.resolution?.implied} />
		{#each notes as note (note)}
			<p class="text-[11px] text-muted-foreground">{note}</p>
		{/each}
		{#each preview?.warnings ?? [] as warning (warning)}
			<p class="flex items-start gap-1.5 text-[11px] text-warning">
				<TriangleAlert class="mt-px size-3 shrink-0" />
				<span>{warning}</span>
			</p>
		{/each}
	</Collapsible.Content>
</Collapsible.Root>
