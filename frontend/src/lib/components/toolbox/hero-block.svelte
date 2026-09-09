<script lang="ts">
	import IdentityMark from './identity-mark.svelte';
	import { TONE_DOT, TONE_METER, TONE_TEXT } from '$lib/config/toolbox';
	import type { ResultBlock } from '$lib/types/toolbox';

	let { block }: { block: ResultBlock } = $props();

	const pct = $derived(Math.round((block.meter?.value ?? 0) * 100));
</script>

<div class="rounded-lg border bg-muted/25 px-4 py-3.5">
	<div class="flex items-start justify-between gap-6">
		<div class="flex min-w-0 items-start gap-2.5">
			{#if block.identity}
				<span class="flex h-6 shrink-0 items-center">
					<IdentityMark identity={block.identity} class="size-5" />
				</span>
			{/if}
			<div class="min-w-0">
				<h3 class="truncate text-[17px] leading-6 font-medium tracking-tight">
					{block.headline}
				</h3>
				{#if block.sub}
					<p class="truncate text-xs text-muted-foreground">{block.sub}</p>
				{/if}
			</div>
		</div>

		{#if block.metric}
			<div class="shrink-0 text-right">
				<div class="text-2xl leading-7 font-semibold tabular-nums {TONE_TEXT[block.metric.tone]}">
					{block.metric.value}
				</div>
				{#if block.metric.label}
					<div class="text-[10px] tracking-wide text-muted-foreground uppercase">
						{block.metric.label}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	{#if block.meter}
		<div class="mt-3">
			<div class="h-1 w-full overflow-hidden rounded-full bg-border">
				<div
					class="h-full rounded-full transition-[width] duration-500 {TONE_METER[block.meter.tone]}"
					style="width: {Math.max(pct, 2)}%"
				></div>
			</div>
			{#if block.meter.caption}
				<p class="mt-1 text-[11px] text-muted-foreground">{block.meter.caption}</p>
			{/if}
		</div>
	{/if}

	{#if block.marks.length}
		<div class="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 border-t pt-2.5">
			{#each block.marks as m (m.label)}
				<span class="flex items-center gap-1.5 text-xs">
					<span class="size-1.5 shrink-0 rounded-full {TONE_DOT[m.tone]}"></span>
					<span class="text-muted-foreground">{m.label}</span>
					{#if m.note}<span class={TONE_TEXT[m.tone]}>{m.note}</span>{/if}
				</span>
			{/each}
		</div>
	{/if}
</div>
