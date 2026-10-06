<script lang="ts">
	import AnswerBody from './answer-body.svelte';
	import { causeLine, leadNumber } from './lead';
	import { surfaceSpec } from '$lib/config/surface';
	import type { AnswerBlock, AskCitation, BlockData } from '$lib/types/ask';

	interface Props {
		block: AnswerBlock | null;
		data: BlockData | undefined;
		text: string;
		citations?: AskCitation[];
		known: Set<string>;
		onRef: (id: string) => void;
	}

	let { block, data, text, citations = [], known, onRef }: Props = $props();

	let total = $derived(data?.error ? null : (data?.total ?? block?.total ?? null));
	let capped = $derived(data?.capped ?? block?.capped ?? false);
	let count = $derived(total == null ? '' : `${total.toLocaleString()}${capped ? '+' : ''}`);
	let spec = $derived(surfaceSpec(block?.dimension ?? ''));
	let title = $derived(block?.title || (total === 1 ? spec?.noun : spec?.nounPlural) || '');
	let lede = $derived(text ? leadNumber(text, total) : null);
	let across = $derived(causeLine(data?.causes, total, capped));
</script>

{#if block && total != null && lede}
	<div class="flex items-baseline gap-3">
		<span class="shrink-0 text-4xl leading-none font-semibold tracking-tight tabular-nums"
			>{count}</span
		>
		<div class="min-w-0 flex-1">
			<AnswerBody text={lede.rest} {citations} blocks={known} large {onRef} />
		</div>
	</div>
{:else}
	{#if block && total != null}
		<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
			<span class="text-4xl leading-none font-semibold tracking-tight tabular-nums">{count}</span>
			<span class="text-lg font-semibold tracking-tight text-balance">{title}</span>
			{#if across}
				<span class="text-sm text-muted-foreground">· {across}</span>
			{/if}
		</div>
	{/if}
	{#if text}
		<AnswerBody {text} {citations} blocks={known} large {onRef} />
	{/if}
{/if}
