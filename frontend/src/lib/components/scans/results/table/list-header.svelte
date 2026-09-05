<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { ACTIONS_BODY, ACTIONS_PIN, type TableColumn } from './columns';

	interface Props {
		lead: TableColumn[];
		columns: TableColumn[];
		selectAllChecked?: boolean | 'indeterminate';
		selectAllLabel?: string;
		onSelectAll?: () => void;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
	}

	let {
		lead,
		columns,
		selectAllChecked,
		selectAllLabel = '',
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
	{#if onSelectAll}
		<div class="hidden shrink-0 sm:flex">
			<Checkbox
				checked={selectAllChecked === true}
				indeterminate={selectAllChecked === 'indeterminate'}
				onCheckedChange={onSelectAll}
				aria-label={selectAllLabel}
			/>
		</div>
	{/if}
	{#each lead as col (col.key)}
		<div
			class="{col.grow === undefined ? '' : col.grow ? 'min-w-0 flex-1' : 'shrink-0'} {col.width}"
		>
			{@render cell(col)}
		</div>
	{/each}
	{#each columns as col (col.key)}
		<div
			class="hidden sm:flex {col.grow ? 'min-w-0 flex-1' : 'shrink-0'} {col.width} {col.align ===
			'right'
				? 'justify-end'
				: ''}"
		>
			{@render cell(col)}
		</div>
	{/each}
	<div class={ACTIONS_PIN}>
		<div class="{ACTIONS_BODY} bg-muted/30"></div>
	</div>
</div>
