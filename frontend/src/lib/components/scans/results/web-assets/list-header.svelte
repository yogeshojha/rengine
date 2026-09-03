<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import type { WebAssetColumn } from './columns';

	interface Props {
		columns: WebAssetColumn[];
		selectAllChecked: boolean | 'indeterminate';
		onSelectAll: () => void;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
	}

	let { columns, selectAllChecked, onSelectAll, sortKey, sortDir, onSort }: Props = $props();
</script>

{#snippet sortable(label: string, key: string)}
	<button
		type="button"
		class="flex items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort(key)}
	>
		{label}
		{#if sortKey === key}
			{#if sortDir === 1}<ArrowUp class="size-3" />{:else}<ArrowDown class="size-3" />{/if}
		{/if}
	</button>
{/snippet}

<div
	class="flex items-center gap-3 border-b bg-muted/30 px-4 py-2 text-xs font-medium tracking-wider text-muted-foreground uppercase"
>
	<div class="hidden shrink-0 sm:flex">
		<Checkbox
			checked={selectAllChecked === true}
			indeterminate={selectAllChecked === 'indeterminate'}
			onCheckedChange={onSelectAll}
			aria-label="Select all hosts on this page"
		/>
	</div>
	<div class="min-w-0 flex-[3] contain-inline-size sm:min-w-56">
		{@render sortable('Host', 'name')}
	</div>
	<div class="w-12 shrink-0 sm:w-16">{@render sortable('Status', 'status')}</div>
	<div class="hidden min-w-40 flex-[2] sm:block">{@render sortable('Title', 'title')}</div>
	{#each columns as col (col.key)}
		<div class="hidden shrink-0 sm:flex {col.width} {col.align === 'right' ? 'justify-end' : ''}">
			{#if col.sort}
				{@render sortable(col.label, col.sort)}
			{:else}
				{col.label}
			{/if}
		</div>
	{/each}
	<div class="w-8 shrink-0 sm:w-14"></div>
</div>
