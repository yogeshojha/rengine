<script lang="ts">
	import type { Snippet } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
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
	<div
		class="flex h-9 min-w-[240px] flex-1 items-center gap-2 rounded-md border bg-background px-2.5 focus-within:ring-2 focus-within:ring-ring/50"
	>
		<Search class="size-4 shrink-0 text-muted-foreground" />
		<input
			class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
			{placeholder}
			bind:value={search}
			aria-label={placeholder}
		/>
		{#if search}
			<button
				type="button"
				class="rounded text-muted-foreground hover:text-foreground"
				aria-label="Clear search"
				onclick={() => (search = '')}><X class="size-3.5" /></button
			>
		{/if}
	</div>
	{#if children}
		<div class="flex flex-wrap items-center gap-2">{@render children()}</div>
	{/if}
</div>
