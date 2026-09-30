<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Copy from '@lucide/svelte/icons/copy';
	import NotebookPen from '@lucide/svelte/icons/notebook-pen';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Bubble from '$lib/components/ui/bubble';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import AskTrace from './ask-trace.svelte';
	import EvidencePeek from './evidence-peek.svelte';
	import { parseAnswer } from './answer-text';
	import {
		ASK_FLAG_LABELS,
		CitationKind,
		EVIDENCE_FIELD_LABELS,
		EvidenceField,
		MessageRole
	} from '$lib/config/ask';
	import type { AskCitation, AskMessage } from '$lib/types/ask';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		message: AskMessage;
		request: string | null;
		response: string | null;
		onOpenEvidence?: () => void;
		onSave?: (text: string) => void;
	}

	let { message, request, response, onOpenEvidence, onSave }: Props = $props();

	let blocks = $derived(parseAnswer(message.text));
	let byNumber = $derived(new Map(message.citations.map((c) => [c.n, c])));
	let peek = $state<{ n: number; block: number } | null>(null);

	function toggle(n: number, block: number) {
		const cite = byNumber.get(n);
		if (!cite || cite.kind === CitationKind.TOOL || !cite.lines.length) return;
		peek = peek?.n === n && peek.block === block ? null : { n, block };
	}

	function evidence(cite: AskCitation): string | null {
		return cite.field === EvidenceField.REQUEST ? request : response;
	}

	function where(flag: { field: keyof typeof EVIDENCE_FIELD_LABELS; line: number }): string {
		const name = EVIDENCE_FIELD_LABELS[flag.field] ?? flag.field;
		return flag.line ? `Line ${flag.line} of the ${name}.` : `In the ${name}.`;
	}

	async function copy() {
		if (await writeClipboard(message.text)) toast.success('Copied');
	}
</script>

{#if message.role === MessageRole.USER}
	<Bubble.Root align="end" variant="muted" class="max-w-[85%] self-end">
		<Bubble.Content class="whitespace-pre-wrap">{message.text}</Bubble.Content>
	</Bubble.Root>
{:else}
	<div class="flex flex-col gap-2.5">
		{#each message.flags as flag, i (i)}
			<div class="flex gap-2.5 rounded-md border border-warning/40 bg-warning/10 p-3">
				<span class="flex h-5 items-center">
					<TriangleAlert class="size-4 text-warning" />
				</span>
				<div class="flex min-w-0 flex-col gap-1">
					<span class="text-xs font-medium">{ASK_FLAG_LABELS[flag.kind] ?? flag.kind}</span>
					<span class="text-2xs text-muted-foreground">{where(flag)}</span>
					<code
						class="rounded border bg-card px-1.5 py-1 font-mono text-2xs wrap-anywhere text-muted-foreground"
						>{flag.sample}</code
					>
				</div>
			</div>
		{/each}

		{#each blocks as block, i (i)}
			{#if block.kind === 'item'}
				<div class="flex gap-2 text-sm leading-relaxed">
					<span class="w-4 shrink-0 pt-px font-mono text-xs text-muted-foreground tabular-nums"
						>{block.n ?? '·'}</span
					>
					<div class="min-w-0 flex-1">{@render spans(block.spans, i)}</div>
				</div>
			{:else}
				<p class="m-0 text-sm leading-relaxed wrap-anywhere">{@render spans(block.spans, i)}</p>
			{/if}
			{#if peek?.block === i}
				{@const cite = byNumber.get(peek.n)}
				{#if cite && cite.field}
					<EvidencePeek
						field={cite.field}
						lines={cite.lines}
						text={evidence(cite)}
						mark={cite.n}
						onOpen={onOpenEvidence}
					/>
				{/if}
			{/if}
		{/each}

		{#if message.trace.length}
			<AskTrace steps={message.trace} />
		{/if}

		<div class="-ml-2 flex items-center gap-0.5">
			<Button variant="ghost" size="sm" class="h-7 gap-1.5 px-2 text-xs" onclick={copy}>
				<Copy />
				Copy
			</Button>
			{#if onSave}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 gap-1.5 px-2 text-xs"
					onclick={() => onSave(message.text)}
				>
					<NotebookPen />
					Save to notes
				</Button>
			{/if}
		</div>
	</div>
{/if}

{#snippet spans(list: ReturnType<typeof parseAnswer>[number]['spans'], block: number)}
	{#each list as span, j (j)}
		{#if span.kind === 'cite'}
			{@const cite = byNumber.get(span.n)}
			{#if !cite}
				<span class="text-muted-foreground">[{span.n}]</span>
			{:else if cite.kind === CitationKind.TOOL && cite.pivot}
				<Hint text={cite.label}>
					{#snippet child(props)}
						<a
							{...props}
							href={cite.pivot}
							class="mx-0.5 inline-flex size-4 items-center justify-center rounded-sm bg-accent align-[1px] font-mono text-2xs font-semibold text-primary"
							>{span.n}</a
						>
					{/snippet}
				</Hint>
			{:else}
				<Hint text={cite.label}>
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							onclick={() => toggle(span.n, block)}
							class="mx-0.5 inline-flex size-4 items-center justify-center rounded-sm bg-accent align-[1px] font-mono text-2xs font-semibold text-primary"
							class:bg-primary={peek?.n === span.n && peek.block === block}
							class:text-primary-foreground={peek?.n === span.n && peek.block === block}
							>{span.n}</button
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
