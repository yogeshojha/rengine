<script lang="ts">
	import { SCAN_WIDTHS } from './scan-columns';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import type { ScanSortKey, ScanSortDir } from '$lib/types/scan';

	interface Props {
		targetId?: string;
		selectable?: boolean;
		selectAllChecked?: boolean | 'indeterminate';
		onSelectAll?: () => void;
		sortKey: ScanSortKey;
		sortDir: ScanSortDir;
		onSort: (key: ScanSortKey) => void;
	}

	let {
		targetId,
		selectable = false,
		selectAllChecked = false,
		onSelectAll,
		sortKey,
		sortDir,
		onSort
	}: Props = $props();
</script>

{#snippet arrow(key: ScanSortKey)}
	{#if sortKey === key}
		{#if sortDir === 'asc'}<ArrowUp class="h-3 w-3" />{:else}<ArrowDown class="h-3 w-3" />{/if}
	{/if}
{/snippet}

<div
	class="flex items-center gap-3 px-4 py-2 border-b border-border bg-muted/30 text-xs font-medium text-muted-foreground uppercase tracking-wider"
>
	{#if selectable}
		<Checkbox
			checked={selectAllChecked === true}
			indeterminate={selectAllChecked === 'indeterminate'}
			onCheckedChange={onSelectAll}
			aria-label="Select all scans"
		/>
	{/if}

	<div class="min-w-0 flex-1">{targetId ? 'Engine' : 'Target'}</div>

	{#if !targetId}
		<div class={SCAN_WIDTHS.engine}>Engine</div>
	{/if}

	<button
		type="button"
		class="{SCAN_WIDTHS.status} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('status')}
	>
		Status
		{@render arrow('status')}
	</button>

	<button
		type="button"
		class="{SCAN_WIDTHS.results} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('subdomains')}
	>
		Results
		{@render arrow('subdomains')}
	</button>

	<button
		type="button"
		class="{SCAN_WIDTHS.duration} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('duration')}
	>
		Duration
		{@render arrow('duration')}
	</button>

	<button
		type="button"
		class="{SCAN_WIDTHS.started} items-center gap-1 uppercase tracking-wider hover:text-foreground"
		onclick={() => onSort('started')}
	>
		Started
		{@render arrow('started')}
	</button>

	<div class={SCAN_WIDTHS.actions}></div>
</div>
