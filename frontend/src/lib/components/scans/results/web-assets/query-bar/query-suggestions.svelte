<script lang="ts">
	import CornerDownLeft from '@lucide/svelte/icons/corner-down-left';
	import Clock from '@lucide/svelte/icons/clock';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import X from '@lucide/svelte/icons/x';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import type { QueryStarter } from '$lib/types/asset-query';
	import type { Suggestion } from './suggest';
	import QueryExample from './query-example.svelte';

	interface Props {
		suggestions: Suggestion[];
		active: number;
		recents: string[];
		examples: QueryStarter[];
		counted: boolean;
		showStarters: boolean;
		moreCount: number;
		onPick: (suggestion: Suggestion) => void;
		onQuery: (query: string) => void;
		onForget: (query: string) => void;
		onHover: (index: number) => void;
		onShowAll: () => void;
		onHelp: () => void;
	}

	let {
		suggestions,
		active,
		recents,
		examples,
		counted,
		showStarters,
		moreCount,
		onShowAll,
		onPick,
		onQuery,
		onForget,
		onHover,
		onHelp
	}: Props = $props();

	let groups = $derived.by(() => {
		const out: { name: string; items: { item: Suggestion; index: number }[] }[] = [];
		suggestions.forEach((item, index) => {
			const bucket = out.find((g) => g.name === item.group);
			if (bucket) bucket.items.push({ item, index });
			else out.push({ name: item.group, items: [{ item, index }] });
		});
		return out;
	});
	let split = $derived(showStarters && recents.length > 0);
	let shownExamples = $derived(split ? examples.slice(0, 4) : examples);
	let columns = $derived(
		shownExamples.length === 1
			? ''
			: !split && shownExamples.length >= 5
				? 'sm:grid-cols-2 lg:grid-cols-3'
				: 'sm:grid-cols-2'
	);
</script>

{#snippet heading(label: string, spark = false)}
	<p
		class="flex items-center gap-1.5 px-2 pt-2 pb-1.5 text-[10px] font-medium tracking-[0.08em] text-muted-foreground uppercase"
	>
		{#if spark}<Sparkles class="size-3 text-primary" />{/if}{label}
	</p>
{/snippet}

<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[min(60vh,24rem)]">
	{#if showStarters}
		<div class="grid gap-x-2 p-2 {split ? 'md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]' : ''}">
			{#if recents.length}
				<div class="flex min-w-0 flex-col md:border-r md:border-border/60 md:pr-2">
					{@render heading('Recent')}
					{#each recents as recent (recent)}
						<div
							class="group/recent flex min-w-0 items-center gap-2 rounded-md pr-1 pl-2 transition-colors hover:bg-accent"
						>
							<Clock class="size-3.5 shrink-0 text-muted-foreground/70" />
							<button
								type="button"
								class="min-w-0 flex-1 truncate py-1.5 text-left font-mono text-xs"
								title={recent}
								onclick={() => onQuery(recent)}
							>
								{recent}
							</button>
							<button
								type="button"
								class="shrink-0 rounded-sm p-1 text-muted-foreground/50 opacity-0 group-hover/recent:opacity-100 hover:text-foreground focus-visible:opacity-100"
								aria-label="Remove {recent} from recent searches"
								onclick={() => onForget(recent)}
							>
								<X class="size-3" />
							</button>
						</div>
					{/each}
				</div>
			{/if}
			{#if shownExamples.length}
				<div class="flex min-w-0 flex-col">
					{@render heading(counted ? 'Findings in this scan' : 'Suggested queries', counted)}
					<div class="grid gap-1.5 px-1 pb-1 {columns}">
						{#each shownExamples as example (example.query)}
							<QueryExample {example} onPick={onQuery} />
						{/each}
					</div>
					{#if counted}
						<button
							type="button"
							class="mx-1 mt-1.5 mb-1 flex items-center justify-center gap-1.5 rounded-md border border-dashed border-border/70 px-3 py-2 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-accent/50 hover:text-foreground"
							onclick={onShowAll}
						>
							{moreCount > 0
								? `Show ${moreCount.toLocaleString()} more ${moreCount === 1 ? 'finding' : 'findings'}`
								: 'Browse all findings'}
							<ArrowRight class="size-3.5" />
						</button>
					{/if}
				</div>
			{/if}
		</div>
	{:else}
		<div id="query-suggestions" role="listbox" class="p-1.5">
			{#each groups as group (group.name)}
				{@render heading(group.name)}
				{#each group.items as entry (entry.item.id)}
					<button
						type="button"
						id="query-option-{entry.index}"
						role="option"
						aria-selected={entry.index === active}
						class="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left transition-colors {entry.index ===
						active
							? 'bg-accent'
							: ''}"
						onmousemove={() => onHover(entry.index)}
						onclick={() => onPick(entry.item)}
					>
						<span
							class="shrink-0 rounded-[3px] font-mono text-xs {entry.item.keepOpen
								? 'bg-primary/10 px-1 py-0.5 text-primary'
								: 'text-foreground'}">{entry.item.label}</span
						>
						{#if entry.item.detail}
							<span class="min-w-0 flex-1 truncate text-xs text-muted-foreground"
								>{entry.item.detail}</span
							>
						{:else}
							<span class="flex-1"></span>
						{/if}
						{#if entry.item.hint}
							{#if entry.item.keepOpen}
								<Badge
									variant="outline"
									class="h-4 shrink-0 px-1 text-[10px] font-normal text-muted-foreground"
									>{entry.item.hint}</Badge
								>
							{:else}
								<span class="shrink-0 text-[11px] text-muted-foreground/70 tabular-nums"
									>{entry.item.hint}</span
								>
							{/if}
						{/if}
						<CornerDownLeft
							class="size-3.5 shrink-0 text-muted-foreground {entry.index === active
								? ''
								: 'invisible'}"
						/>
					</button>
				{/each}
			{/each}
		</div>
	{/if}
</ScrollArea>

<div
	class="flex items-center gap-3 border-t bg-muted/30 px-3 py-1.5 text-[11px] text-muted-foreground"
>
	{#if showStarters}
		<span class="flex items-center gap-1 max-sm:hidden"><Kbd>↵</Kbd> search</span>
		<span class="flex items-center gap-1 max-sm:hidden"
			><Kbd>Tab</Kbd> completes fields and values as you type</span
		>
	{:else}
		<span class="flex items-center gap-1 max-sm:hidden"><Kbd>Tab</Kbd> complete</span>
		<span class="flex items-center gap-1 max-sm:hidden"
			><Kbd>↵</Kbd> {active >= 0 ? 'insert' : 'search'}</span
		>
		<span class="flex items-center gap-1 max-sm:hidden"><Kbd>↑</Kbd><Kbd>↓</Kbd> choose</span>
		<span class="flex items-center gap-1 max-sm:hidden"><Kbd>Esc</Kbd> dismiss</span>
	{/if}
	<Button
		variant="ghost"
		size="sm"
		class="ml-auto h-6 gap-1.5 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
		onclick={onHelp}
	>
		<CircleQuestionMark class="size-3.5" />
		Syntax guide
	</Button>
</div>
