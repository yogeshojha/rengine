<script lang="ts">
	import ListFilter from '@lucide/svelte/icons/list-filter';
	import Check from '@lucide/svelte/icons/check';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import { cn } from '$lib/utils';
	import type { Snippet } from 'svelte';
	import {
		MAX_CHIP_QUERY,
		MENU_SUGGESTIONS,
		SUGGESTION_CHARS,
		SUGGESTIONS_SHOWN,
		SUGGESTIONS_WITH_CHIPS,
		toolbarChips,
		valuesLabel,
		type ExtraChip,
		type FacetSpec,
		type FilterSuggestion,
		type SignalSpec
	} from './filter-toolbar';

	interface Props {
		facets: FacetSpec[];
		signals?: SignalSpec[];
		extras?: ExtraChip[];
		suggestions?: FilterSuggestion[];
		onSuggest?: (suggestion: FilterSuggestion) => void;
		onClear: () => void;
		/** the sort, view and more menus */
		tools?: Snippet;
		class?: string;
	}

	let {
		facets,
		signals = [],
		extras = [],
		suggestions = [],
		onSuggest,
		onClear,
		tools,
		class: klass = ''
	}: Props = $props();

	let open = $state(false);
	let level = $state<string | null>(null);
	let search = $state('');

	let chips = $derived(toolbarChips(facets, signals, extras));
	let active = $derived(facets.find((f) => f.key === level) ?? null);
	let shownSuggestions = $derived.by(() => {
		const fitting = suggestions.filter((s) => s.query.length <= MAX_CHIP_QUERY);
		const limit = chips.length ? SUGGESTIONS_WITH_CHIPS : SUGGESTIONS_SHOWN;
		const shown: FilterSuggestion[] = [];
		let used = chips.reduce((n, c) => n + c.label.length + valuesLabel(c.values).length, 0);
		for (const s of fitting) {
			if (shown.length >= limit) break;
			if (shown.length >= 2 && used + s.query.length > SUGGESTION_CHARS) break;
			shown.push(s);
			used += s.query.length + 6;
		}
		return shown;
	});
	// menu rows pinned at open
	let pinned = $state<FilterSuggestion[]>([]);
	let menuSuggestions = $derived(
		pinned.map((p) => suggestions.find((s) => s.query === p.query) ?? { ...p, count: null })
	);

	function pin() {
		pinned = suggestions.slice(0, MENU_SUGGESTIONS);
	}

	function openAt(key: string | null) {
		level = key;
		search = '';
		pin();
		open = true;
	}

	function onOpenChange(next: boolean) {
		open = next;
		if (next) pin();
		else {
			level = null;
			search = '';
		}
	}

	function back() {
		level = null;
		search = '';
	}

	function toggle(facet: FacetSpec, value: string) {
		if (facet.single) {
			facet.onChange(facet.selected.includes(value) ? [] : [value]);
			return;
		}
		facet.onChange(
			facet.selected.includes(value)
				? facet.selected.filter((v) => v !== value)
				: [...facet.selected, value]
		);
	}

	function onInputKeydown(e: KeyboardEvent) {
		if (e.key === 'Backspace' && !search && level) {
			e.preventDefault();
			back();
		}
	}

	function suggest(suggestion: FilterSuggestion) {
		onSuggest?.(suggestion);
		open = false;
	}
</script>

{#snippet box(on: boolean)}
	<span
		class={cn(
			'flex size-4 shrink-0 items-center justify-center rounded-sm border',
			on
				? 'border-primary bg-primary text-primary-foreground'
				: 'border-muted-foreground/40 [&_svg]:invisible'
		)}
	>
		<Check class="size-3" />
	</span>
{/snippet}

{#snippet count(n: number | null | undefined, capped?: boolean)}
	{#if n != null}
		<span class="ml-auto pl-3 text-xs text-muted-foreground tabular-nums">
			{n.toLocaleString()}{capped ? '+' : ''}
		</span>
	{/if}
{/snippet}

<div class={cn('flex items-start gap-2 border-b px-3 py-2', klass)}>
	<div class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
		<Popover.Root {open} {onOpenChange}>
			<Popover.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="outline"
						size="sm"
						class={chips.length ? 'border-primary/50 bg-primary/5' : ''}
						aria-label={chips.length ? `Filter, ${chips.length} active` : 'Filter'}
					>
						<ListFilter class="size-4" />
						Filter
						{#if chips.length}
							<Badge variant="secondary" class="h-5 px-1.5 font-mono text-2xs">{chips.length}</Badge
							>
						{/if}
					</Button>
				{/snippet}
			</Popover.Trigger>
			<Popover.Content class="w-72 p-0" align="start">
				<Command.Root loop>
					<Command.Input
						placeholder={active ? active.label : 'Filter by'}
						bind:value={search}
						onkeydown={onInputKeydown}
					/>
					<Command.List class="max-h-80">
						<Command.Empty>No matches</Command.Empty>
						{#if active}
							{#if !search}
								<Command.Group>
									<Command.Item
										value="__back"
										onSelect={back}
										class="text-muted-foreground"
										aria-label="Back to filters"
									>
										<ChevronLeft class="size-3.5" />
										<span class="text-xs">Filters</span>
										<span class="ml-auto text-xs font-medium text-foreground">{active.label}</span>
									</Command.Item>
								</Command.Group>
								<Command.Separator />
							{/if}
							<Command.Group>
								{#if active.loading}
									<div class="flex flex-col gap-2 px-2 py-2" aria-hidden="true">
										{#each { length: 4 } as _, i (i)}
											<Skeleton class="h-4 w-full" />
										{/each}
									</div>
								{:else}
									{#each active.options as option (option.value)}
										{@const on = active.selected.includes(option.value)}
										<Command.Item
											value={option.value}
											keywords={[option.label]}
											onSelect={() => toggle(active, option.value)}
										>
											{@render box(on)}
											<span class={cn('truncate', active.mono && 'font-mono text-xs')}
												>{option.label}</span
											>
											{@render count(option.count)}
										</Command.Item>
									{/each}
								{/if}
							</Command.Group>
							{#if active.selected.length}
								<Command.Separator />
								<Command.Group>
									<Command.Item
										value="__clear"
										onSelect={() => active?.onChange([])}
										class="justify-center text-muted-foreground"
									>
										Clear {active.label.toLowerCase()}
									</Command.Item>
								</Command.Group>
							{/if}
						{:else}
							{#if menuSuggestions.length && !search}
								<Command.Group heading="Suggested">
									{#each menuSuggestions as suggestion (suggestion.query)}
										<Command.Item
											value={`suggest ${suggestion.query}`}
											keywords={[suggestion.description]}
											onSelect={() => suggest(suggestion)}
										>
											<Plus class="size-3.5" />
											<span class="truncate font-mono text-xs">{suggestion.query}</span>
											{@render count(suggestion.count, suggestion.capped)}
										</Command.Item>
									{/each}
								</Command.Group>
								<Command.Separator />
							{/if}
							{#if facets.length}
								<Command.Group heading="Filters">
									{#each facets as facet (facet.key)}
										<Command.Item
											value={facet.label}
											onSelect={() => {
												level = facet.key;
												search = '';
											}}
										>
											<span class="truncate">{facet.label}</span>
											{#if facet.selected.length}
												<Badge variant="secondary" class="ml-auto h-5 px-1.5 font-mono text-2xs">
													{facet.selected.length}
												</Badge>
												<ChevronRight class="size-3.5" />
											{:else}
												<ChevronRight class="ml-auto size-3.5" />
											{/if}
										</Command.Item>
									{/each}
								</Command.Group>
							{/if}
							{#if signals.length}
								{#if facets.length}<Command.Separator />{/if}
								<Command.Group heading="Signals">
									{#each signals as signal (signal.key)}
										<Command.Item value={signal.label} onSelect={signal.onToggle}>
											{@render box(signal.on)}
											<span class="truncate">{signal.label}</span>
											{@render count(signal.count)}
										</Command.Item>
									{/each}
								</Command.Group>
							{/if}
						{/if}
					</Command.List>
				</Command.Root>
			</Popover.Content>
		</Popover.Root>

		{#each chips as chip (chip.id)}
			<span
				class="inline-flex h-8 max-w-full items-stretch overflow-hidden rounded-md border bg-background text-xs"
				role="group"
				aria-label="Filter {chip.label}"
			>
				{#if chip.facet}
					<button
						type="button"
						class="flex min-w-0 items-center gap-1.5 px-2 hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						onclick={() => openAt(chip.facet)}
						aria-label="Edit filter {chip.label}"
					>
						<span class="shrink-0 text-muted-foreground">{chip.label}</span>
						<span class={cn('truncate font-medium', chip.mono && 'font-mono')}
							>{valuesLabel(chip.values)}</span
						>
					</button>
				{:else}
					<span class={cn('flex min-w-0 items-center px-2 font-medium', chip.mono && 'font-mono')}>
						<span class="truncate">{chip.label}</span>
					</span>
				{/if}
				<button
					type="button"
					class="flex shrink-0 items-center border-l px-1.5 text-muted-foreground hover:bg-muted/60 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					onclick={chip.onRemove}
					aria-label="Remove filter {chip.label}"
				>
					<X class="size-3" />
				</button>
			</span>
		{/each}

		{#if chips.length}
			<Button
				variant="ghost"
				size="sm"
				class="text-muted-foreground"
				onclick={() => onClear()}
				aria-label="Clear all filters"
			>
				Clear
			</Button>
		{/if}

		{#each shownSuggestions as suggestion (suggestion.query)}
			<Hint text={suggestion.description}>
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						class="hidden h-8 max-w-full items-center gap-1.5 rounded-md border border-dashed px-2 text-xs text-muted-foreground hover:border-primary/50 hover:bg-primary/5 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none md:inline-flex"
						onclick={() => suggest(suggestion)}
						aria-label={suggestion.count == null
							? `Add filter ${suggestion.query}`
							: `Add filter ${suggestion.query}, ${suggestion.count}${suggestion.capped ? '+' : ''} rows`}
					>
						<Plus class="size-3 shrink-0" />
						<span class="truncate font-mono">{suggestion.query}</span>
						{#if suggestion.count != null}
							<span class="shrink-0 tabular-nums"
								>{suggestion.count.toLocaleString()}{suggestion.capped ? '+' : ''}</span
							>
						{/if}
					</button>
				{/snippet}
			</Hint>
		{/each}
	</div>
	{#if tools}
		<div class="ml-auto flex shrink-0 items-center gap-2">
			{@render tools()}
		</div>
	{/if}
</div>
