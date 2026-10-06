<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import {
		parseAnswer,
		type AnswerSpan
	} from '$lib/components/scans/results/vulnerabilities/ask/answer-text';
	import { CitationKind } from '$lib/config/ask';
	import { inAppHref } from '$lib/utilities/mcp';
	import type { AskCitation } from '$lib/types/ask';

	interface Props {
		text: string;
		citations?: AskCitation[];
		blocks?: Set<string>;
		large?: boolean;
		onRef?: (id: string) => void;
	}

	let { text, citations = [], blocks, large = false, onRef }: Props = $props();

	let size = $derived(large ? 'text-base leading-7' : 'text-sm leading-6');

	let parsed = $derived(parseAnswer(text));
	let byNumber = $derived(new Map(citations.map((c) => [c.n, c])));
</script>

{#snippet spans(list: AnswerSpan[])}
	{#each list as span, j (j)}
		{#if span.kind === 'block'}
			{#if !blocks || blocks.has(span.id)}
				<button
					type="button"
					class="ml-0.5 inline-flex h-4 items-center rounded-sm bg-primary/10 px-1 font-mono text-2xs font-semibold text-primary hover:bg-primary/20"
					onclick={() => onRef?.(span.id)}
					aria-label="Go to {span.id}">{span.id}</button
				>
			{/if}
		{:else if span.kind === 'cite'}
			{@const cite = byNumber.get(span.n)}
			{#if cite?.kind === CitationKind.TOOL && cite.pivot}
				<Hint text={cite.label}>
					{#snippet child(props)}
						<a
							{...props}
							href={inAppHref(cite.pivot ?? '')}
							class="mx-0.5 inline-flex size-4 items-center justify-center rounded-sm bg-accent font-mono text-2xs font-semibold text-primary"
							>{span.n}</a
						>
					{/snippet}
				</Hint>
			{/if}
		{:else if span.kind === 'bold'}
			<b class="font-semibold">{span.text}</b>
		{:else if span.kind === 'code'}
			<code class="rounded bg-muted px-1 font-mono text-xs">{span.text}</code>
		{:else}
			{span.text}
		{/if}
	{/each}
{/snippet}

<div class="flex flex-col gap-2.5">
	{#each parsed as block, i (i)}
		{#if block.kind === 'item'}
			<div class="flex gap-2 {size}">
				<span class="w-4 shrink-0 pt-px font-mono text-xs text-muted-foreground tabular-nums"
					>{block.n ?? '·'}</span
				>
				<div class="min-w-0 flex-1">{@render spans(block.spans)}</div>
			</div>
		{:else}
			<p class="m-0 wrap-anywhere {size}">{@render spans(block.spans)}</p>
		{/if}
	{/each}
</div>
