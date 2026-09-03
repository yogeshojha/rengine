<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Plus from '@lucide/svelte/icons/plus';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { lex } from '$lib/utilities/query-lexer';
	import type { QueryFieldSpec, QuerySchema } from '$lib/types/asset-query';
	import QueryHighlight from './query-highlight.svelte';

	interface Props {
		open: boolean;
		schema: QuerySchema;
		noun: string;
		onOpenChange: (open: boolean) => void;
		onInsert: (fragment: string) => void;
	}

	let { open, schema, noun, onOpenChange, onInsert }: Props = $props();

	const ANATOMY: Record<string, string> = {
		host: 'is:live and status:>=400 and not (cdn:yes or waf:yes)',
		address: 'is:open and ports:>2 and not (cdn:yes or country=US)'
	};
	const SECTIONS = [
		{ id: 'grammar', label: 'Grammar' },
		{ id: 'fields', label: 'Fields' },
		{ id: 'flags', label: 'Flags' }
	];

	let filter = $state('');
	let needle = $derived(filter.trim().toLowerCase());

	let known = $derived.by(() => {
		const names = new Set(schema.fields.flatMap((f) => [f.name, ...f.aliases]));
		return (name: string) => names.has(name);
	});
	let dates = $derived(schema.fields.filter((f) => f.type === 'date'));
	let sample = $derived(ANATOMY[noun] ?? ANATOMY.host);
	let anatomy = $derived(lex(sample, known));

	let groups = $derived.by(() => {
		const match = (field: QueryFieldSpec) =>
			!needle ||
			field.name.includes(needle) ||
			field.aliases.some((a) => a.includes(needle)) ||
			field.description.toLowerCase().includes(needle) ||
			field.values.some((v) => v.includes(needle));
		return schema.groups
			.map((name) => ({ name, fields: schema.fields.filter((f) => f.group === name && match(f)) }))
			.filter((g) => g.fields.length > 0);
	});
	let flags = $derived(
		schema.flags.filter(
			(f) => !needle || f.value.includes(needle) || f.description.toLowerCase().includes(needle)
		)
	);

	function insert(fragment: string) {
		onInsert(fragment);
		onOpenChange(false);
	}
	function jump(id: string) {
		document
			.getElementById(`query-help-${id}`)
			?.scrollIntoView({ block: 'start', behavior: 'smooth' });
	}
</script>

{#snippet label(text: string)}
	<h3 class="text-[10px] font-medium tracking-[0.08em] text-muted-foreground uppercase">{text}</h3>
{/snippet}

{#snippet key(text: string)}
	<span class="rounded-[3px] bg-primary/10 px-1 py-0.5 font-mono text-xs text-primary">{text}</span>
{/snippet}

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		<Sheet.Header class="gap-1 border-b p-5 pb-4">
			<Sheet.Title>Search syntax</Sheet.Title>
			<Sheet.Description>
				Type words to search everything, or narrow with a field. Terms combine with and, or and not.
			</Sheet.Description>
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<InputGroup.Root class="min-w-56 flex-1">
					<InputGroup.Addon><Search /></InputGroup.Addon>
					<InputGroup.Input
						bind:value={filter}
						placeholder="Filter fields and flags"
						aria-label="Filter fields and flags"
						autocomplete="off"
					/>
				</InputGroup.Root>
				{#if !needle}
					<div class="flex items-center gap-0.5">
						{#each SECTIONS as section (section.id)}
							<Button
								variant="ghost"
								size="sm"
								class="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
								onclick={() => jump(section.id)}
							>
								{section.label}
							</Button>
						{/each}
					</div>
				{/if}
			</div>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col gap-7 p-5">
				{#if !needle}
					<section class="rounded-lg border bg-muted/30 p-4">
						{@render label('How a query reads')}
						<p class="mt-2.5 font-mono text-sm leading-7 break-all whitespace-pre-wrap">
							<QueryHighlight source={sample} tokens={anatomy.tokens} problems={[]} />
						</p>
						<div
							class="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground"
						>
							<span class="flex items-center gap-1.5"
								>{@render key('field:')} narrows to one property</span
							>
							<span class="flex items-center gap-1.5"
								><span class="font-mono text-foreground">value</span> what it must match</span
							>
							<span class="flex items-center gap-1.5"
								><span class="font-mono font-semibold text-info">and</span> joins terms</span
							>
							<span class="flex items-center gap-1.5"
								><span class="font-mono">( )</span> groups a clause</span
							>
						</div>
					</section>

					<section id="query-help-grammar" class="grid scroll-mt-5 gap-6 sm:grid-cols-2">
						<div class="flex flex-col gap-2.5">
							{@render label('Compare values')}
							<dl class="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1.5 text-xs">
								{#each schema.operators as operator (operator.symbol)}
									<dt>{@render key(operator.symbol)}</dt>
									<dd class="text-muted-foreground">{operator.description}</dd>
								{/each}
							</dl>
							{#if dates.length}
								<p class="text-xs text-muted-foreground">
									Dates take a calendar date or an age.
									<span class="font-mono">{dates[0].name}:&lt;7d</span> is the last week.
								</p>
							{/if}
						</div>
						<div class="flex flex-col gap-2.5">
							{@render label('Combine terms')}
							<dl class="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1.5 text-xs">
								{#each schema.connectors as connector (connector.symbol)}
									<dt>
										<span class="rounded-[3px] bg-info/10 px-1 py-0.5 font-mono text-xs text-info"
											>{connector.symbol}</span
										>
									</dt>
									<dd class="text-muted-foreground">{connector.description}</dd>
								{/each}
							</dl>
						</div>
					</section>
				{/if}

				{#if groups.length === 0 && flags.length === 0}
					<EmptyState
						icon={SearchX}
						title="No fields match"
						description="Try a shorter word."
						class="border-0 bg-transparent"
					/>
				{/if}

				{#if groups.length}
					<section id="query-help-fields" class="flex scroll-mt-5 flex-col gap-1">
						<div class="flex items-baseline justify-between">
							{@render label('Fields')}
							<span class="text-[11px] text-muted-foreground">Click one to add it to the query</span
							>
						</div>
						{#each groups as group (group.name)}
							<div class="relative">
								<h4
									class="sticky top-0 z-10 bg-background/95 py-2 text-xs font-medium backdrop-blur"
								>
									{group.name}
								</h4>
								<div class="divide-y divide-border/50">
									{#each group.fields as field (field.name)}
										<button
											type="button"
											class="group -mx-2 grid w-[calc(100%+1rem)] grid-cols-[8.5rem_minmax(0,1fr)_auto] items-start gap-x-3 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-accent/50"
											onclick={() => insert(field.name === 'is' ? 'is:' : `${field.name}:`)}
										>
											<span class="flex min-w-0 flex-col items-start gap-1">
												{@render key(`${field.name}:`)}
												{#if field.aliases.length}
													<span class="truncate font-mono text-[11px] text-muted-foreground/70"
														>{field.aliases.join(', ')}</span
													>
												{/if}
											</span>
											<span class="flex min-w-0 flex-col gap-1">
												<span class="text-xs text-foreground">{field.description}</span>
												<span
													class="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-muted-foreground/80"
												>
													<Badge
														variant="outline"
														class="h-4 px-1 font-sans text-[10px] font-normal text-muted-foreground"
														>{field.type}</Badge
													>
													<span>{field.example}</span>
													{#if field.values.length && field.name !== 'is'}
														<span>{field.values.join(' · ')}</span>
													{/if}
												</span>
											</span>
											<Plus
												class="mt-0.5 size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
											/>
										</button>
									{/each}
								</div>
							</div>
						{/each}
					</section>
				{/if}

				{#if flags.length}
					<section id="query-help-flags" class="flex scroll-mt-5 flex-col gap-2.5">
						<div class="flex items-baseline justify-between">
							{@render label('Flags')}
							<span class="text-[11px] text-muted-foreground"
								>Properties of {noun === 'host' ? 'a host' : 'an address'}, used as
								<span class="font-mono">is:{schema.flags[0]?.value ?? 'live'}</span></span
							>
						</div>
						<div class="grid gap-x-4 gap-y-0.5 sm:grid-cols-2">
							{#each flags as flag (flag.value)}
								<button
									type="button"
									class="flex min-w-0 items-center gap-2.5 rounded-md px-1.5 py-1.5 text-left transition-colors hover:bg-accent/50"
									onclick={() => insert(`is:${flag.value} `)}
								>
									{@render key(`is:${flag.value}`)}
									<span class="truncate text-xs text-muted-foreground">{flag.description}</span>
								</button>
							{/each}
						</div>
					</section>
				{/if}
			</div>
		</ScrollArea>

		<div
			class="flex items-center gap-3 border-t bg-muted/30 px-5 py-2 text-[11px] text-muted-foreground"
		>
			<span class="flex items-center gap-1"><Kbd>/</Kbd> focus search</span>
			<span class="flex items-center gap-1"><Kbd>?</Kbd> open this guide</span>
			<span class="flex items-center gap-1"><Kbd>Tab</Kbd> accept a suggestion</span>
		</div>
	</Sheet.Content>
</Sheet.Root>
