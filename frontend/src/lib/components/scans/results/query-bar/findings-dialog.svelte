<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Switch } from '$lib/components/ui/switch';
	import { Label } from '$lib/components/ui/label';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SearchX from '@lucide/svelte/icons/search-x';
	import type { QueryLeads } from '$lib/types/asset-query';
	import QueryExample from './query-example.svelte';

	interface Props {
		open: boolean;
		leadSet: QueryLeads | null;
		noun: string;
		nounPlural: string;
		groups: string[];
		onOpenChange: (open: boolean) => void;
		onQuery: (query: string) => void;
	}

	let { open, leadSet, noun, nounPlural, groups, onOpenChange, onQuery }: Props = $props();

	let showEmpty = $state(false);

	let leads = $derived(leadSet?.leads ?? []);
	let matched = $derived(leads.filter((lead) => lead.count > 0));
	let shown = $derived(showEmpty ? leads : matched);
	let sections = $derived.by(() => {
		const names = groups.length ? groups : [...new Set(shown.map((lead) => lead.group))];
		return names
			.map((name) => ({ name, leads: shown.filter((lead) => lead.group === name) }))
			.filter((section) => section.leads.length > 0);
	});
	let scope = $derived.by(() => {
		if (!leadSet) return '';
		const rows = `${leadSet.total.toLocaleString()}${leadSet.total_capped ? '+' : ''}`;
		const word = leadSet.total === 1 ? noun : nounPlural;
		const where = leadSet.filtered ? ' in view' : '';
		return `${matched.length} of ${leads.length} queries matched · ${rows} ${word}${where}`;
	});

	function apply(query: string) {
		onQuery(query);
		onOpenChange(false);
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Matched queries</Dialog.Title>
		</Dialog.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col gap-5 px-6 py-5">
				{#if sections.length === 0}
					<EmptyState
						icon={SearchX}
						title="No queries matched"
						compact
						class="border-0 bg-transparent"
					/>
				{/if}
				{#each sections as section (section.name)}
					<section class="flex flex-col gap-2">
						<h3 class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
							{section.name}
						</h3>
						<div class="grid gap-2 sm:grid-cols-2">
							{#each section.leads as lead (lead.query)}
								<QueryExample example={lead} {noun} {nounPlural} onPick={apply} />
							{/each}
						</div>
					</section>
				{/each}
			</div>
		</ScrollArea>

		<div class="flex flex-wrap items-center justify-between gap-3 border-t px-6 py-4">
			<span class="text-xs text-muted-foreground">{scope}</span>
			<div class="flex items-center gap-2">
				<Switch id="findings-show-empty" bind:checked={showEmpty} />
				<Label for="findings-show-empty">Show queries with no matches</Label>
			</div>
		</div>
	</Dialog.Content>
</Dialog.Root>
