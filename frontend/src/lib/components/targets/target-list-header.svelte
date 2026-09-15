<script lang="ts">
	import { TARGET_WIDTHS } from './target-columns';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
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
		checked={selectAllChecked === true}
		indeterminate={selectAllChecked === 'indeterminate'}
		onCheckedChange={onSelectAll}
	/>

	<button
		type="button"
		class="{TARGET_WIDTHS.name} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('name')}
	>
		Target
		{@render arrow('name')}
	</button>

	<button
		type="button"
		class="{TARGET_WIDTHS.type} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('type')}
	>
		Type
		{@render arrow('type')}
	</button>

	<div class={TARGET_WIDTHS.organizations}>Organizations</div>
	<div class={TARGET_WIDTHS.tags}>Tags</div>

	<button
		type="button"
		class="{TARGET_WIDTHS.updated} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('updated')}
	>
		Updated
		{@render arrow('updated')}
	</button>

	<div class="flex shrink-0 gap-1">
		<div class="w-8"></div>
		<div class="w-8"></div>
	</div>
</div>
