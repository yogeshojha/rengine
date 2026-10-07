<script lang="ts">
	import Layers from '@lucide/svelte/icons/layers';
	import type { IconComponent } from '$lib/config/icons';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
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
		class="h-auto min-w-[9.5rem] flex-1 flex-col items-stretch justify-start gap-1.5 rounded-none border-r px-4 py-3 text-left font-normal whitespace-normal last:border-r-0 hover:bg-accent/30 data-[state=on]:bg-accent/50"
	>
		<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
			<Icon class="size-3.5" />
			<span class="truncate">{label}</span>
		</span>
		<span class="flex items-baseline gap-1.5">
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

<div class="border-b">
	<ScrollArea.Root orientation="horizontal" class="w-full">
		<ToggleGroup.Root
			type="single"
			spacing={1}
			value={active}
			onValueChange={(v) => v && onSelect(v)}
			aria-label="Result dimension"
			class="w-full min-w-max gap-0 rounded-none"
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
	</ScrollArea.Root>
</div>
