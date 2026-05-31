<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { ArrowDown, ArrowUp } from 'lucide-svelte';
	import type { SortDir, SortKey } from '$lib/utilities/target-signals';

	interface Props {
		selectAllChecked: boolean | 'indeterminate';
		onSelectAll: () => void;
		sortKey: SortKey;
		sortDir: SortDir;
		onSort: (key: SortKey) => void;
	}

	let { selectAllChecked, onSelectAll, sortKey, sortDir, onSort }: Props = $props();
</script>

<div
	class="flex items-center gap-3 px-4 py-2 border-b border-border bg-muted/30 text-xs font-medium text-muted-foreground uppercase tracking-wider"
>
	<Checkbox
		checked={selectAllChecked === 'indeterminate' ? undefined : selectAllChecked}
		onCheckedChange={onSelectAll}
	/>

	<button
		type="button"
		class="w-[240px] flex items-center gap-1 uppercase tracking-wider hover:text-foreground transition-colors"
		onclick={() => onSort('name')}
	>
		Target
		{#if sortKey === 'name'}
			{#if sortDir === 'asc'}
				<ArrowUp class="h-3 w-3" />
			{:else}
				<ArrowDown class="h-3 w-3" />
			{/if}
		{/if}
	</button>
	<div class="w-[120px]">Scans</div>
	<div class="hidden md:block flex-1 min-w-[180px]">Organizations</div>
	<div class="hidden lg:block flex-1 min-w-[200px]">Tags</div>
	<button
		type="button"
		class="hidden sm:flex w-[80px] items-center justify-end gap-1 uppercase tracking-wider hover:text-foreground transition-colors"
		onclick={() => onSort('updated')}
	>
		Updated
		{#if sortKey === 'updated'}
			{#if sortDir === 'asc'}
				<ArrowUp class="h-3 w-3" />
			{:else}
				<ArrowDown class="h-3 w-3" />
			{/if}
		{/if}
	</button>

	<div class="flex gap-1">
		<div class="w-8"></div>
		<div class="w-8"></div>
	</div>
</div>
