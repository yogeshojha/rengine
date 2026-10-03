<script lang="ts">
	import { untrack } from 'svelte';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CopyButton from '$lib/components/copy-button.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { wordlistsApi } from '$lib/api/wordlists';
	import {
		WORDLIST_KIND_LABELS,
		WORDLIST_ORIGIN_BADGE,
		WORDLIST_ORIGIN_LABELS,
		type Wordlist
	} from '$lib/types/wordlist';

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
			failed =
				e instanceof Error
					? e.message
					: 'The API did not respond. Check that the api service is running.';
		} finally {
			loading = false;
		}
	}
</script>

<Sheet.Root open={!!wordlist} {onOpenChange}>
	<Sheet.Content class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		{#if wordlist}
			<Sheet.Header class="gap-2 border-b px-5 py-4 pr-12">
				<Sheet.Title class="wrap-anywhere">{wordlist.name}</Sheet.Title>
				{#if wordlist.description}
					<Sheet.Description>{wordlist.description}</Sheet.Description>
				{/if}
				<div class="flex flex-wrap items-center gap-2 pt-1">
					<Badge variant={WORDLIST_ORIGIN_BADGE[wordlist.origin]}>
						{WORDLIST_ORIGIN_LABELS[wordlist.origin]}
					</Badge>
					<Badge variant="outline">{WORDLIST_KIND_LABELS[wordlist.kind]}</Badge>
					<span class="font-mono text-xs tabular-nums text-muted-foreground">
						{wordlist.words.toLocaleString()} words
					</span>
				</div>
				<div class="flex items-center gap-1">
					<code class="rounded-md border bg-muted/60 px-1.5 py-0.5 font-mono text-xs">
						{wordlist.slug}
					</code>
					<CopyButton value={wordlist.slug} />
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				{#if loading}
					<div class="flex flex-col gap-2 px-5 py-4" aria-busy="true">
						<Skeleton class="h-4 w-2/3" />
						<Skeleton class="h-4 w-1/2" />
						<Skeleton class="h-4 w-3/5" />
					</div>
				{:else if failed}
					<div class="px-5 py-4">
						<EmptyState
							compact
							icon={TriangleAlert}
							title="Wordlist not loaded"
							description={failed}
						>
							<Button size="sm" variant="outline" onclick={() => wordlist && load(wordlist.id)}
								>Retry</Button
							>
						</EmptyState>
					</div>
				{:else}
					<ol class="divide-y font-mono text-xs">
						{#each words as word, index (index)}
							<li class="flex gap-4 px-5 py-1.5">
								<span class="w-8 shrink-0 text-right tabular-nums text-muted-foreground"
									>{index + 1}</span
								>
								<span class="min-w-0 break-all">{word}</span>
							</li>
						{/each}
					</ol>
					{#if wordlist.words > words.length}
						<p class="px-5 py-3 text-xs text-muted-foreground">
							First {words.length} of {wordlist.words.toLocaleString()}
						</p>
					{/if}
				{/if}
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
