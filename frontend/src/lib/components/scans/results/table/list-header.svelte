<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import type { TableColumn } from './columns';

	interface Props {
		lead: TableColumn[];
		columns: TableColumn[];
		selectAllChecked: boolean | 'indeterminate';
		selectAllLabel: string;
		onSelectAll: () => void;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
	}

	let {
		lead,
		columns,
		selectAllChecked,
		selectAllLabel,
		onSelectAll,
		sortKey,
		sortDir,
		onSort
	}: Props = $props();
</script>

{#snippet cell(col: TableColumn)}
	{#if col.sort}
		<button
			type="button"
			class="flex items-center gap-1 uppercase tracking-wider hover:text-foreground"
			onclick={() => onSort(col.sort ?? col.key)}
		>
			{col.label}
			{#if sortKey === col.sort}
				{#if sortDir === 1}<ArrowUp class="size-3" />{:else}<ArrowDown class="size-3" />{/if}
			{/if}
		</button>
	{:else}
		{col.label}
	{/if}
{/snippet}

<div
	class="flex items-center gap-3 border-b bg-muted/30 px-4 py-2 text-xs font-medium tracking-wider text-muted-foreground uppercase"
>
	<div class="hidden shrink-0 sm:flex">
		<Checkbox
			checked={selectAllChecked === true}
			indeterminate={selectAllChecked === 'indeterminate'}
			onCheckedChange={onSelectAll}
			aria-label={selectAllLabel}
		/>
	</div>
	{#each lead as col (col.key)}
		<div class={col.width}>{@render cell(col)}</div>
	{/each}
	{#each columns as col (col.key)}
		<div class="hidden shrink-0 sm:flex {col.width} {col.align === 'right' ? 'justify-end' : ''}">
			{@render cell(col)}
		</div>
	{/each}
	<div class="w-8 shrink-0 sm:w-14"></div>
</div>
