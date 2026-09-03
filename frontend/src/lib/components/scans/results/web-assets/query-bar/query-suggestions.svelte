<script lang="ts">
	import CornerDownLeft from '@lucide/svelte/icons/corner-down-left';
	import Clock from '@lucide/svelte/icons/clock';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import X from '@lucide/svelte/icons/x';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Kbd } from '$lib/components/ui/kbd';
	import type { QueryExampleSpec } from '$lib/types/asset-query';
	import type { Suggestion } from './suggest';

	interface Props {
		suggestions: Suggestion[];
		active: number;
		recents: string[];
		examples: QueryExampleSpec[];
		showStarters: boolean;
		onPick: (suggestion: Suggestion) => void;
		onQuery: (query: string) => void;
		onForget: (query: string) => void;
		onHover: (index: number) => void;
	}

	let {
		suggestions,
		active,
		recents,
		examples,
		showStarters,
		onPick,
		onQuery,
		onForget,
		onHover
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
</script>

<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[min(60vh,22rem)]">
	<div class="p-1.5">
		{#if showStarters}
			{#if recents.length}
				<p
					class="flex items-center gap-1.5 px-2 pt-1 pb-1.5 text-xs font-medium text-muted-foreground"
				>
					<Clock class="h-3.5 w-3.5" /> Recent
				</p>
				<div class="flex flex-wrap gap-1.5 px-2 pb-1">
					{#each recents as recent (recent)}
						<span
							class="group/chip inline-flex max-w-[15rem] items-center rounded-md border border-input bg-accent/60 py-1 pr-1 pl-2 transition-colors hover:border-primary/50 hover:bg-accent"
						>
							<button
								type="button"
								class="min-w-0 truncate font-mono text-[11px]"
								title={recent}
								onclick={() => onQuery(recent)}
							>
								{recent}
							</button>
							<button
								type="button"
								class="ml-1 shrink-0 rounded-sm text-muted-foreground/50 opacity-0 group-hover/chip:opacity-100 hover:text-foreground focus-visible:opacity-100"
								aria-label="Remove {recent} from recent searches"
								onclick={() => onForget(recent)}
							>
								<X class="h-3 w-3" />
							</button>
						</span>
					{/each}
				</div>
			{/if}
			{#if examples.length}
				<p
					class="flex items-center gap-1.5 px-2 pt-2 pb-1.5 text-xs font-medium text-muted-foreground"
				>
					<Sparkles class="h-3.5 w-3.5" /> Try
				</p>
				{#each examples as example (example.query)}
					<button
						type="button"
						class="flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-1.5 text-left hover:bg-accent"
						onclick={() => onQuery(example.query)}
					>
						<span class="font-mono text-xs text-primary">{example.query}</span>
						<span class="text-xs text-muted-foreground">{example.description}</span>
					</button>
				{/each}
			{/if}
		{:else}
			{#each groups as group (group.name)}
				<p class="px-2 pt-1.5 pb-1 text-[11px] font-medium tracking-wide text-muted-foreground">
					{group.name}
				</p>
				{#each group.items as entry (entry.item.id)}
					<button
						type="button"
						id="query-option-{entry.index}"
						role="option"
						aria-selected={entry.index === active}
						class="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left {entry.index ===
						active
							? 'bg-accent'
							: ''}"
						onmousemove={() => onHover(entry.index)}
						onclick={() => onPick(entry.item)}
					>
						<span class="shrink-0 font-mono text-xs text-primary">{entry.item.label}</span>
						{#if entry.item.detail}
							<span class="min-w-0 flex-1 truncate text-xs text-muted-foreground"
								>{entry.item.detail}</span
							>
						{:else}
							<span class="flex-1"></span>
						{/if}
						{#if entry.item.hint}
							<span class="shrink-0 text-[11px] tabular-nums text-muted-foreground/70"
								>{entry.item.hint}</span
							>
						{/if}
						{#if entry.index === active}
							<CornerDownLeft class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
						{/if}
					</button>
				{/each}
			{/each}
		{/if}
	</div>
</ScrollArea>

{#if !showStarters && suggestions.length}
	<div
		class="flex items-center gap-3 border-t px-3 py-1.5 text-[11px] text-muted-foreground max-sm:hidden"
	>
		<span class="flex items-center gap-1"><Kbd>↑</Kbd><Kbd>↓</Kbd> navigate</span>
		<span class="flex items-center gap-1"><Kbd>Tab</Kbd> complete</span>
		<span class="flex items-center gap-1"><Kbd>Esc</Kbd> dismiss</span>
	</div>
{/if}
