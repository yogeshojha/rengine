<script lang="ts">
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { kindIcon, sourceChipClass, sourceIcon } from '$lib/config/interest';
	import { INTEREST_SOURCE, type InterestSignal } from '$lib/types/interest';

	interface Props {
		signal: InterestSignal;
		onPick?: (kind: string) => void;
	}

	let { signal, onPick }: Props = $props();

	let isAi = $derived(signal.source === INTEREST_SOURCE.AI);
	let Icon = $derived(isAi ? sourceIcon(signal.source) : kindIcon(signal.kind));
	let help = $derived(interestCatalog.kind(signal.kind)?.help ?? '');
</script>

<HoverCard.Root openDelay={140}>
	<HoverCard.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				type="button"
				class="inline-flex items-center gap-1 rounded border px-1.5 py-px text-[10px] font-medium {sourceChipClass(
					signal.source
				)}"
				onclick={(e) => {
					e.stopPropagation();
					onPick?.(signal.kind);
				}}
			>
				<Icon class="size-2.5" />
				{signal.kind_label}
			</button>
		{/snippet}
	</HoverCard.Trigger>
	<HoverCard.Content class="w-80 max-w-[90vw] p-3" side="top" align="start">
		<p class="flex items-center gap-1.5 text-xs font-medium">
			{signal.kind_label}
			<span
				class="rounded border px-1 py-px text-[10px] font-normal {sourceChipClass(signal.source)}"
				>{interestCatalog.sourceLabel(signal.source)}</span
			>
		</p>
		{#if signal.reason}
			<p class="mt-1.5 text-xs text-muted-foreground">{signal.reason}</p>
		{:else if help}
			<p class="mt-1.5 text-xs text-muted-foreground">{help}</p>
		{/if}
		{#if isAi && signal.model}
			<p class="mt-2 text-[11px] text-muted-foreground">
				Written by {signal.model}. A judgement, not an observation.
			</p>
		{:else if signal.evidence}
			<p
				class="mt-2 rounded border border-border bg-accent/50 p-2 font-mono text-[11px] break-all text-muted-foreground"
			>
				{signal.evidence}
			</p>
		{/if}
	</HoverCard.Content>
</HoverCard.Root>
