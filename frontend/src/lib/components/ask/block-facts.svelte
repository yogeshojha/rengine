<script lang="ts">
	import { linkScan } from './link-scope';
	import { blockHref } from './block-columns';
	import type { BlockFact } from '$lib/types/ask';

	interface Props {
		total: number;
		capped: boolean;
		facts: BlockFact[];
		disabled?: boolean;
		dimension: string | null;
		scopeValues: string[] | null;
		links?: boolean;
		onFact?: (fact: BlockFact) => void;
	}

	let {
		total,
		capped,
		facts,
		disabled = false,
		dimension,
		scopeValues,
		links = false,
		onFact
	}: Props = $props();

	const scan = linkScan();

	const CHIP =
		'inline-flex h-7 items-center gap-1.5 rounded-md border bg-background px-2.5 text-xs text-muted-foreground hover:border-primary/30 hover:bg-muted/40 hover:text-foreground';
</script>

{#if facts.length}
	<div class="flex flex-col gap-2 border-t px-4 py-3">
		<span class="text-2xs font-medium tracking-wide text-muted-foreground uppercase"
			>Within these {total.toLocaleString()}{capped ? '+' : ''}</span
		>
		<div class="flex flex-wrap gap-2">
			{#each facts as fact (fact.query)}
				{@const href = links ? blockHref(dimension, fact.query, scopeValues, scan()) : null}
				{#snippet body()}
					<b class="font-semibold text-foreground tabular-nums"
						>{fact.count.toLocaleString()}{fact.capped ? '+' : ''}</b
					>
					{fact.title}
				{/snippet}
				{#if href}
					<a {href} class={CHIP}>{@render body()}</a>
				{:else}
					<button
						type="button"
						{disabled}
						class="{CHIP} disabled:opacity-60"
						onclick={() => onFact?.(fact)}
					>
						{@render body()}
					</button>
				{/if}
			{/each}
		</div>
	</div>
{/if}
