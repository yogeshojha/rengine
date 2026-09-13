<script lang="ts">
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Layers from '@lucide/svelte/icons/layers';
	import X from '@lucide/svelte/icons/x';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { Button } from '$lib/components/ui/button';
	import ExportMenu from '../export-menu.svelte';
	import SortMenu from './sort-menu.svelte';
	import type { SortOption, TableColumn } from './columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';

	interface Props {
		dimension: string;
		dimensions: QueryGroupSpec[];
		groupBy: string;
		onGroupBy: (key: string) => void;
		sorts: SortOption[];
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		columns: TableColumn[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
		refreshing: boolean;
		onRefresh: () => void;
		projectId?: string;
		scanId?: string;
		exportFilters?: Record<string, unknown>;
		showGroupBy?: boolean;
		showColumns?: boolean;
		columnsLocked?: boolean;
	}

	let {
		dimension,
		dimensions,
		groupBy,
		onGroupBy,
		sorts,
		sortKey,
		sortDir,
		onSort,
		columns,
		visible,
		onToggleColumn,
		density,
		onDensity,
		refreshing,
		onRefresh,
		projectId = '',
		scanId = '',
		exportFilters = {},
		showGroupBy = true,
		showColumns = true,
		columnsLocked = false
	}: Props = $props();

	let groupLabel = $derived(dimensions.find((d) => d.key === groupBy)?.label ?? 'Group');
</script>

{#if showGroupBy && dimensions.length}
	<ButtonGroup>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="outline"
						size="sm"
						class="h-9 gap-2 {groupBy ? 'border-primary/50 bg-primary/5' : ''}"
					>
						<Layers class="h-4 w-4" />
						<span class="hidden sm:inline">{groupLabel}</span>
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="max-h-none w-52 overflow-visible">
				<DropdownMenu.Label>Group by</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
					<DropdownMenu.RadioGroup value={groupBy} onValueChange={onGroupBy}>
						<DropdownMenu.RadioItem value="">No grouping</DropdownMenu.RadioItem>
						{#each dimensions as groupDimension (groupDimension.key)}
							<DropdownMenu.RadioItem value={groupDimension.key}>
								{groupDimension.label}
							</DropdownMenu.RadioItem>
						{/each}
					</DropdownMenu.RadioGroup>
				</ScrollArea>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
		{#if groupBy}
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9 border-primary/50 bg-primary/5 text-muted-foreground hover:text-foreground"
				aria-label="Clear grouping"
				onclick={() => onGroupBy('')}
			>
				<X class="h-4 w-4" />
			</Button>
		{/if}
	</ButtonGroup>
{/if}

{#if !groupBy}
	<SortMenu {sorts} {sortKey} {sortDir} {onSort} />
{/if}

{#if !groupBy && showColumns}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
					<Columns3 class="h-4 w-4" />
					<span class="hidden sm:inline">Columns</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="max-h-none w-44 overflow-visible">
			{#if !columnsLocked}
				<DropdownMenu.Group>
					<DropdownMenu.Label>Columns</DropdownMenu.Label>
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-64">
						{#each columns as col (col.key)}
							<DropdownMenu.CheckboxItem
								checked={visible.includes(col.key)}
								onCheckedChange={() => onToggleColumn(col.key)}
								closeOnSelect={false}
							>
								{col.label}
							</DropdownMenu.CheckboxItem>
						{/each}
					</ScrollArea>
				</DropdownMenu.Group>
				<DropdownMenu.Separator />
			{/if}
			<DropdownMenu.Group>
				<DropdownMenu.Label>Density</DropdownMenu.Label>
				<DropdownMenu.RadioGroup value={density} onValueChange={onDensity}>
					<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
					<DropdownMenu.RadioItem value="cozy">Cozy</DropdownMenu.RadioItem>
				</DropdownMenu.RadioGroup>
			</DropdownMenu.Group>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}

<ExportMenu {dimension} {projectId} {scanId} filters={exportFilters} />
<Button
	variant="outline"
	size="icon"
	class="h-9 w-9"
	aria-label="Refresh"
	onclick={() => onRefresh()}
	disabled={refreshing}
>
	<RefreshCw class="h-4 w-4 {refreshing ? 'animate-spin' : ''}" />
</Button>
