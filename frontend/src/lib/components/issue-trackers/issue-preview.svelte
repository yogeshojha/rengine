<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CodeBlock from '$lib/components/code-block.svelte';
	import type { CodeLang } from '$lib/utilities/code-highlight';
	import type { PreviewBlock } from '$lib/types/issue-tracker';

	interface Props {
		blocks: PreviewBlock[];
	}

	let { blocks }: Props = $props();

	const LANGS = new Set<string>(['http', 'shell']);
	const lang = (value: string): CodeLang => (LANGS.has(value) ? (value as CodeLang) : 'text');
</script>

<div class="flex min-h-0 flex-col rounded-md border">
	<div class="border-b px-3 py-2 text-xs font-medium text-muted-foreground">Description</div>
	<ScrollArea class="min-h-0 [&_[data-slot=scroll-area-viewport]]:max-h-80">
		<div class="flex flex-col gap-3 px-3 py-3">
			{#each blocks as block, i (i)}
				{#if block.kind === 'heading'}
					<h4 class="pt-1 text-sm font-semibold">{block.text}</h4>
				{:else if block.kind === 'paragraph'}
					<p class="text-sm leading-relaxed wrap-anywhere">{block.text}</p>
				{:else if block.kind === 'facts'}
					<dl class="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
						{#each block.items as [label, value] (label)}
							<dt class="text-muted-foreground">{label}</dt>
							<dd class="wrap-anywhere">{value}</dd>
						{/each}
					</dl>
				{:else if block.kind === 'code'}
					<CodeBlock code={block.text} lang={lang(block.lang)} numbers={false} wrap maxLines={12} />
				{:else if block.kind === 'list'}
					<ul class="flex list-disc flex-col gap-0.5 pl-5 font-mono text-xs">
						{#each block.lines as line, j (j)}
							<li class="wrap-anywhere">{line}</li>
						{/each}
					</ul>
				{:else if block.kind === 'link'}
					<a
						href={block.href}
						target="_blank"
						rel="noopener noreferrer"
						class="w-fit text-sm text-primary">{block.text}</a
					>
				{/if}
			{/each}
		</div>
	</ScrollArea>
</div>
