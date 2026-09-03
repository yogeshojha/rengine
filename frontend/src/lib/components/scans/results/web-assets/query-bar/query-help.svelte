<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SearchX from '@lucide/svelte/icons/search-x';
	import type { QueryFieldSpec, QuerySchema } from '$lib/types/asset-query';

	interface Props {
		open: boolean;
		schema: QuerySchema;
		onOpenChange: (open: boolean) => void;
		onInsert: (fragment: string) => void;
		onQuery: (query: string) => void;
	}

	let { open, schema, onOpenChange, onInsert, onQuery }: Props = $props();

	let filter = $state('');

	let groups = $derived.by(() => {
		const needle = filter.trim().toLowerCase();
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
			(f) =>
				!filter.trim() ||
				f.value.includes(filter.trim().toLowerCase()) ||
				f.description.toLowerCase().includes(filter.trim().toLowerCase())
		)
	);

	function apply(query: string) {
		onQuery(query);
		onOpenChange(false);
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		<Sheet.Header class="gap-1 border-b p-5">
			<Sheet.Title>Search syntax</Sheet.Title>
			<Sheet.Description>
				Type words to search everything, or narrow with a field. Terms combine with and, or and not.
			</Sheet.Description>
			<InputGroup.Root class="mt-3">
				<InputGroup.Addon><Search /></InputGroup.Addon>
				<InputGroup.Input
					bind:value={filter}
					placeholder="Filter fields"
					aria-label="Filter fields"
					autocomplete="off"
				/>
			</InputGroup.Root>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col gap-6 p-5">
				{#if !filter.trim() && schema.examples.length}
					<section class="flex flex-col gap-2">
						<h3 class="text-sm font-medium">Start here</h3>
						<div class="flex flex-col gap-1">
							{#each schema.examples as example (example.query)}
								<button
									type="button"
									class="group flex items-start justify-between gap-3 rounded-md border border-transparent px-2 py-1.5 text-left hover:border-border hover:bg-muted/40"
									onclick={() => apply(example.query)}
								>
									<span class="flex min-w-0 flex-col gap-0.5">
										<span class="font-mono text-xs break-all text-primary">{example.query}</span>
										<span class="text-xs text-muted-foreground">{example.description}</span>
									</span>
									<ArrowUpRight
										class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100"
									/>
								</button>
							{/each}
						</div>
					</section>
					<Separator />
				{/if}

				{#if !filter.trim()}
					<section class="flex flex-col gap-2">
						<h3 class="text-sm font-medium">Combining terms</h3>
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs">
							{#each schema.connectors as connector (connector.symbol)}
								<dt class="font-mono text-info">{connector.symbol}</dt>
								<dd class="text-muted-foreground">{connector.description}</dd>
							{/each}
						</dl>
					</section>
					<section class="flex flex-col gap-2">
						<h3 class="text-sm font-medium">Comparing values</h3>
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs">
							{#each schema.operators as operator (operator.symbol)}
								<dt class="font-mono text-primary">{operator.symbol}</dt>
								<dd class="text-muted-foreground">{operator.description}</dd>
							{/each}
						</dl>
						<p class="text-xs text-muted-foreground">
							Dates take a calendar date or an age: <span class="font-mono">discovered:&lt;7d</span>
							is the last week,
							<span class="font-mono">cert.expires:&lt;30d</span> is the next month.
						</p>
					</section>
					<Separator />
				{/if}

				{#if groups.length === 0 && flags.length === 0}
					<EmptyState
						icon={SearchX}
						title="No fields match"
						description="Try a shorter word."
						class="border-0 bg-transparent"
					/>
				{/if}

				{#each groups as group (group.name)}
					<section class="flex flex-col gap-2">
						<h3 class="text-sm font-medium">{group.name}</h3>
						<div class="flex flex-col divide-y divide-border/60">
							{#each group.fields as field (field.name)}
								<button
									type="button"
									class="group flex flex-col gap-1 py-2 text-left"
									onclick={() => {
										onInsert(field.name === 'is' ? 'is:' : `${field.name}:`);
										onOpenChange(false);
									}}
								>
									<span class="flex flex-wrap items-center gap-2">
										<span class="font-mono text-xs text-primary">{field.name}</span>
										<Badge variant="outline" class="h-4 px-1 text-[10px] font-normal"
											>{field.type}</Badge
										>
										{#each field.aliases as alias (alias)}
											<span class="font-mono text-[11px] text-muted-foreground/70">{alias}</span>
										{/each}
									</span>
									<span class="text-xs text-muted-foreground">{field.description}</span>
									{#if field.values.length && field.name !== 'is'}
										<span class="font-mono text-[11px] text-muted-foreground/70">
											{field.values.join(' · ')}
										</span>
									{/if}
									<span class="font-mono text-[11px] text-muted-foreground/70">{field.example}</span
									>
								</button>
							{/each}
						</div>
					</section>
				{/each}

				{#if flags.length}
					<section class="flex flex-col gap-2">
						<h3 class="text-sm font-medium">Flags for <span class="font-mono">is:</span></h3>
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs">
							{#each flags as flag (flag.value)}
								<dt class="font-mono text-primary">is:{flag.value}</dt>
								<dd class="text-muted-foreground">{flag.description}</dd>
							{/each}
						</dl>
					</section>
				{/if}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>
