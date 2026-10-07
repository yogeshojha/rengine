<script lang="ts">
	import Layers from '@lucide/svelte/icons/layers';
	import type { IconComponent } from '$lib/config/icons';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import ChangeBar from './change-bar.svelte';
	import { cn } from '$lib/utils';
	import { COMPARE_TAB_ALL } from '$lib/config/compare';
	import { surfaceSpec } from '$lib/config/surface';
	import { COMPARABILITY, listedCount, type DimensionDelta } from '$lib/types/compare';
	import { pluralWord } from '$lib/utilities/strings';

	interface Props {
		dimensions: DimensionDelta[];
		total: number;
		active: string;
		onSelect: (key: string) => void;
	}

	let { dimensions, total, active, onSelect }: Props = $props();

	let matched = $derived(dimensions.reduce((n, d) => n + d.unchanged + d.changed, 0));
	let tiles = $derived(dimensions.length + 1);
</script>

{#snippet card(
	key: string,
	label: string,
	Icon: IconComponent,
	count: number | null,
	foot: string,
	delta: DimensionDelta | null
)}
	<ToggleGroup.Item
		value={key}
		class="h-auto min-w-0 flex-col items-stretch justify-start gap-1.5 rounded-none border-t border-l px-3 py-3 text-left font-normal whitespace-normal hover:bg-accent/30 data-[state=on]:bg-accent/50 @7xl:px-4"
	>
		<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
			<Icon class="size-3.5" />
			<span class="truncate">{label}</span>
		</span>
		<span class="flex flex-wrap items-baseline gap-x-1.5">
			{#if count === null}
				<span class="text-sm text-muted-foreground">Not scanned</span>
			{:else}
				<span
					class={cn(
						'text-2xl leading-7 font-semibold tabular-nums',
						count === 0 && 'text-muted-foreground/60'
					)}>{count.toLocaleString()}</span
				>
				<span class="text-xs text-muted-foreground">{pluralWord(count, 'change')}</span>
			{/if}
		</span>
		{#if delta}
			<ChangeBar {delta} />
		{:else}
			<span class="h-1"></span>
		{/if}
		<span class="truncate text-2xs text-muted-foreground tabular-nums">{foot}</span>
	</ToggleGroup.Item>
{/snippet}

<!-- Two balanced rows of tiles until the strip is wide enough (72rem) for one. -->
<div
	class="@container overflow-hidden border-b"
	style="--tiles: {tiles}; --tiles-half: {Math.ceil(tiles / 2)}"
>
	<ToggleGroup.Root
		type="single"
		spacing={1}
		value={active}
		onValueChange={(v) => v && onSelect(v)}
		aria-label="Result dimension"
		class="-mt-px -ml-px grid w-[calc(100%+1px)] grid-cols-[repeat(var(--tiles-half),minmax(0,1fr))] gap-0 rounded-none @6xl:grid-cols-[repeat(var(--tiles),minmax(0,1fr))]"
	>
		{@render card(
			COMPARE_TAB_ALL,
			'All changes',
			Layers,
			total,
			`${matched.toLocaleString()} rows matched`,
			null
		)}
		{#each dimensions as d (d.dimension)}
			{@const spec = surfaceSpec(d.dimension)}
			{@const covered = d.verdict.comparability !== COMPARABILITY.NOT_COVERED}
			{@render card(
				d.dimension,
				d.label,
				spec?.icon ?? Layers,
				covered ? listedCount(d) : null,
				covered
					? `${d.total_baseline.toLocaleString()} → ${d.total_current.toLocaleString()}`
					: d.verdict.note,
				covered ? d : null
			)}
		{/each}
	</ToggleGroup.Root>
</div>
