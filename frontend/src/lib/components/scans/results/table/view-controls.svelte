<script lang="ts">
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Layers from '@lucide/svelte/icons/layers';
	import X from '@lucide/svelte/icons/x';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { Button } from '$lib/components/ui/button';
	import ExportMenu from '../export-menu.svelte';
	import TripwireButton from '$lib/components/tripwires/tripwire-button.svelte';
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
		/** chosen columns with no room at this width */
		folded?: string[];
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
		folded = [],
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
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props: tip })}
						<DropdownMenu.Trigger {...tip}>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="outline"
									class={groupBy ? 'border-primary/50 bg-primary/5' : ''}
									aria-label={groupBy ? `Group by ${groupLabel}` : 'Group by'}
								>
									<Layers class="h-4 w-4" />
									<span class="hidden 2xl:inline">{groupLabel}</span>
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content class="2xl:hidden">
					{groupBy ? `Grouped by ${groupLabel}` : 'Group by'}
				</Tooltip.Content>
			</Tooltip.Root>
			<DropdownMenu.Content align="end" class="w-52">
				<DropdownMenu.Label>Group by</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.RadioGroup value={groupBy} onValueChange={onGroupBy}>
					<DropdownMenu.RadioItem value="">No grouping</DropdownMenu.RadioItem>
					{#each dimensions as groupDimension (groupDimension.key)}
						<DropdownMenu.RadioItem value={groupDimension.key}>
							{groupDimension.label}
						</DropdownMenu.RadioItem>
					{/each}
				</DropdownMenu.RadioGroup>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
		{#if groupBy}
			<Button
				variant="outline"
				size="icon"
				class="border-primary/50 bg-primary/5 text-muted-foreground hover:text-foreground"
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
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props: tip })}
					<DropdownMenu.Trigger {...tip}>
						{#snippet child({ props })}
							<Button {...props} variant="outline" aria-label="Columns">
								<Columns3 class="h-4 w-4" />
								<span class="hidden 2xl:inline">Columns</span>
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content class="2xl:hidden">Columns</Tooltip.Content>
		</Tooltip.Root>
		<DropdownMenu.Content align="end" class="w-60">
			{#if !columnsLocked}
				<DropdownMenu.Group>
					<DropdownMenu.Label>Columns</DropdownMenu.Label>
					{#each columns as col (col.key)}
						<DropdownMenu.CheckboxItem
							checked={visible.includes(col.key)}
							onCheckedChange={() => onToggleColumn(col.key)}
							closeOnSelect={false}
						>
							{col.label}
							{#if folded.includes(col.key)}
								<span class="ms-auto text-2xs text-muted-foreground">Hidden at this width</span>
							{/if}
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Group>
				<DropdownMenu.Separator />
			{/if}
			<DropdownMenu.Group>
				<DropdownMenu.Label>Density</DropdownMenu.Label>
				<DropdownMenu.RadioGroup value={density} onValueChange={onDensity}>
					<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
					<DropdownMenu.RadioItem value="cozy">Comfortable</DropdownMenu.RadioItem>
				</DropdownMenu.RadioGroup>
			</DropdownMenu.Group>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}

<ExportMenu {dimension} {projectId} {scanId} filters={exportFilters} />
<TripwireButton
	{dimension}
	{projectId}
	scanId={scanId || null}
	query={typeof exportFilters.q === 'string' ? exportFilters.q : ''}
/>
<Button
	variant="outline"
	size="icon"
	aria-label="Refresh"
	onclick={() => onRefresh()}
	disabled={refreshing}
>
	<RefreshCw class="h-4 w-4 {refreshing ? 'animate-spin' : ''}" />
</Button>
