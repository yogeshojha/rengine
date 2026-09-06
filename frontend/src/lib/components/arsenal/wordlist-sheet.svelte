<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Copy from '@lucide/svelte/icons/copy';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { wordlistsApi } from '$lib/api/wordlists';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { WORDLIST_KIND_LABELS, type Wordlist } from '$lib/types/wordlist';

	interface Props {
		wordlist: Wordlist | null;
		onOpenChange: (open: boolean) => void;
	}

	let { wordlist, onOpenChange }: Props = $props();

	const PREVIEW = 200;

	let words = $state<string[]>([]);
	let loading = $state(false);
	let failed = $state<string | null>(null);

	$effect(() => {
		const item = wordlist;
		if (!item) return;
		untrack(() => load(item.id));
	});

	async function load(id: string) {
		loading = true;
		failed = null;
		words = [];
		try {
			words = await wordlistsApi.preview(id, PREVIEW);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not read this wordlist';
		} finally {
			loading = false;
		}
	}
</script>

<Sheet.Root open={!!wordlist} {onOpenChange}>
	<Sheet.Content class="flex w-full flex-col p-0 sm:max-w-xl">
		{#if wordlist}
			<Sheet.Header class="space-y-2 border-b px-6 py-5">
				<Sheet.Title>{wordlist.name}</Sheet.Title>
				<Sheet.Description>{wordlist.description || 'No description.'}</Sheet.Description>
				<div class="flex flex-wrap items-center gap-2 pt-1">
					<Badge variant={wordlist.origin === 'builtin' ? 'secondary' : 'info'}>
						{wordlist.origin === 'builtin' ? 'Shipped' : 'Uploaded'}
					</Badge>
					<Badge variant="outline">{WORDLIST_KIND_LABELS[wordlist.kind]}</Badge>
					<span class="font-mono text-xs tabular-nums text-muted-foreground">
						{wordlist.words.toLocaleString()} words
					</span>
				</div>
				<div class="flex items-center gap-2 pt-1">
					<code class="rounded border bg-muted/60 px-1.5 py-0.5 font-mono text-xs">
						{wordlist.slug}
					</code>
					<Button
						variant="ghost"
						size="icon"
						class="size-7"
						aria-label="Copy the name a scan engine uses"
						onclick={async () => {
							if (await writeClipboard(wordlist.slug)) toast.success('Name copied');
						}}
					>
						<Copy class="size-3.5" />
					</Button>
				</div>
			</Sheet.Header>

			<div class="min-h-0 flex-1">
				{#if loading}
					<div class="space-y-2 p-6">
						<Skeleton class="h-4 w-2/3" />
						<Skeleton class="h-4 w-1/2" />
						<Skeleton class="h-4 w-3/5" />
					</div>
				{:else if failed}
					<p class="p-6 text-sm text-destructive">{failed}</p>
				{:else}
					<ScrollArea class="h-full [&_[data-slot=scroll-area-viewport]]:max-h-[calc(100vh-14rem)]">
						<ol class="divide-y font-mono text-xs">
							{#each words as word, index (index)}
								<li class="flex gap-4 px-6 py-1.5">
									<span class="w-8 shrink-0 text-right tabular-nums text-muted-foreground"
										>{index + 1}</span
									>
									<span class="min-w-0 break-all">{word}</span>
								</li>
							{/each}
						</ol>
						{#if wordlist.words > words.length}
							<p class="px-6 py-3 text-xs text-muted-foreground">
								First {words.length} of {wordlist.words.toLocaleString()}. A scan reads from the
								top, so the word budget takes this order.
							</p>
						{/if}
					</ScrollArea>
				{/if}
			</div>
		{/if}
	</Sheet.Content>
</Sheet.Root>
