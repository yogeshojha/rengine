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

{#snippet arrow(key: SortKey)}
	{#if sortKey === key}
		{#if sortDir === 'asc'}
			<ArrowUp class="h-3 w-3" />
		{:else}
			<ArrowDown class="h-3 w-3" />
		{/if}
	{/if}
{/snippet}

<div
	class="flex items-center gap-3 px-4 py-2 border-b border-border bg-muted/30 text-xs font-medium text-muted-foreground uppercase tracking-wider"
>
	<Checkbox
		checked={selectAllChecked === 'indeterminate' ? undefined : selectAllChecked}
		onCheckedChange={onSelectAll}
	/>

	<button
		type="button"
		class="flex w-[210px] items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('name')}
	>
		Target
		{@render arrow('name')}
	</button>

	<button
		type="button"
		class="hidden w-[84px] items-center gap-1 uppercase tracking-wider hover:text-foreground sm:flex"
		onclick={() => onSort('type')}
	>
		Type
		{@render arrow('type')}
	</button>

	<button
		type="button"
		class="hidden min-w-[160px] flex-1 items-center gap-1 uppercase tracking-wider hover:text-foreground lg:flex"
		onclick={() => onSort('expiry')}
	>
		Registrar / Exp
		{@render arrow('expiry')}
	</button>

	<div class="hidden w-[150px] xl:block">DNS / BGP</div>
	<div class="hidden w-[110px] xl:block">Related</div>
	<div class="hidden flex-1 md:block min-w-[130px]">Organizations</div>
	<div class="hidden flex-1 lg:block min-w-[130px]">Tags</div>

	<button
		type="button"
		class="hidden w-[84px] items-center justify-end gap-1 uppercase tracking-wider hover:text-foreground sm:flex"
		onclick={() => onSort('updated')}
	>
		Updated
		{@render arrow('updated')}
	</button>

	<div class="flex gap-1">
		<div class="w-8"></div>
		<div class="w-8"></div>
	</div>
</div>
