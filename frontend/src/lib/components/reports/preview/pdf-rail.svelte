<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { visible } from '$lib/utilities/visible';
	import { cn } from '$lib/utils.js';
	import PdfPage from './pdf-page.svelte';
	import type { OutlineEntry, PageSize } from '$lib/utilities/pdf';
	import type { PDFDocumentProxy } from 'pdfjs-dist';

	const THUMB_WIDTH = 112;

	let {
		doc,
		sizes,
		outline,
		page,
		onPick
	}: {
		doc: PDFDocumentProxy;
		sizes: PageSize[];
		outline: OutlineEntry[];
		page: number;
		onPick: (page: number) => void;
	} = $props();

	let tab = $state<'pages' | 'contents'>('pages');
	let pagesViewport = $state<HTMLElement | null>(null);
	const live = new SvelteSet<number>();

	const activeEntry = $derived.by(() => {
		let found = -1;
		outline.forEach((entry, index) => {
			if (entry.page !== null && entry.page <= page) found = index;
		});
		return found;
	});

	$effect(() => {
		const number = page;
		const node = pagesViewport?.querySelector<HTMLElement>(`[data-thumb="${number}"]`);
		node?.scrollIntoView({ block: 'nearest' });
	});
</script>

<div class="hidden w-[9.5rem] shrink-0 flex-col border-r sm:flex">
	{#if outline.length}
		<Tabs.Root bind:value={tab} class="min-h-0 flex-1 gap-0">
			<Tabs.List class="h-8 w-full rounded-none border-b bg-transparent p-0">
				<Tabs.Trigger value="pages" class="h-8 rounded-none text-xs">Pages</Tabs.Trigger>
				<Tabs.Trigger value="contents" class="h-8 rounded-none text-xs">Contents</Tabs.Trigger>
			</Tabs.List>
			<Tabs.Content value="pages" class="min-h-0 flex-1">
				{@render thumbnails()}
			</Tabs.Content>
			<Tabs.Content value="contents" class="min-h-0 flex-1">
				<ScrollArea class="h-full">
					<div class="flex flex-col py-1.5">
						{#each outline as entry, index (index)}
							<button
								type="button"
								disabled={entry.page === null}
								onclick={() => entry.page && onPick(entry.page)}
								class={cn(
									'hover:bg-accent flex items-baseline gap-2 px-3 py-1.5 text-left text-xs disabled:opacity-50',
									index === activeEntry && 'text-foreground font-medium',
									index !== activeEntry && 'text-muted-foreground'
								)}
								style="padding-left:{0.75 + entry.depth * 0.6}rem"
							>
								<span class="min-w-0 flex-1 break-words">{entry.title}</span>
								{#if entry.page !== null}
									<span class="text-muted-foreground shrink-0 tabular-nums">{entry.page}</span>
								{/if}
							</button>
						{/each}
					</div>
				</ScrollArea>
			</Tabs.Content>
		</Tabs.Root>
	{:else}
		{@render thumbnails()}
	{/if}
</div>

{#snippet thumbnails()}
	<ScrollArea class="h-full" bind:viewportRef={pagesViewport}>
		<div class="flex flex-col items-center gap-3 py-3">
			{#each sizes as size, index (index)}
				{@const number = index + 1}
				<button
					type="button"
					data-thumb={number}
					onclick={() => onPick(number)}
					class="flex flex-col items-center gap-1"
					use:visible={{
						root: pagesViewport,
						margin: '150% 0px',
						onChange: (on) => (on ? live.add(number) : live.delete(number))
					}}
				>
					<PdfPage
						{doc}
						{number}
						{size}
						scale={THUMB_WIDTH / size.width}
						active={live.has(number)}
						class={cn(
							'rounded-[2px] ring-1 transition-shadow',
							number === page ? 'ring-primary ring-2' : 'ring-border/70 hover:ring-foreground/30'
						)}
					/>
					<span
						class={cn(
							'text-[10px] tabular-nums',
							number === page ? 'text-foreground font-medium' : 'text-muted-foreground'
						)}
					>
						{number}
					</span>
				</button>
			{/each}
		</div>
	</ScrollArea>
{/snippet}
