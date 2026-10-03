<script lang="ts">
	import type { Snippet } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import * as InputGroup from '$lib/components/ui/input-group';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import { LIBRARY_TABS } from '$lib/config/reports';

	let {
		tab = $bindable(),
		search = $bindable(),
		counts,
		placeholder,
		children
	}: {
		tab: string;
		search: string;
		counts: Record<string, number>;
		placeholder: string;
		children?: Snippet;
	} = $props();
</script>

<div class="border-b px-2">
	<CountTabs tabs={LIBRARY_TABS} value={tab} {counts} onChange={(k) => (tab = k)} />
</div>

<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
	<InputGroup.Root class="h-9 w-auto min-w-[240px] flex-1">
		<InputGroup.Addon>
			<Search />
		</InputGroup.Addon>
		<InputGroup.Input bind:value={search} {placeholder} aria-label={placeholder} />
		{#if search}
			<InputGroup.Addon align="inline-end">
				<InputGroup.Button size="icon-xs" aria-label="Clear search" onclick={() => (search = '')}>
					<X />
				</InputGroup.Button>
			</InputGroup.Addon>
		{/if}
	</InputGroup.Root>
	{#if children}
		<div class="flex flex-wrap items-center gap-2">{@render children()}</div>
	{/if}
</div>
