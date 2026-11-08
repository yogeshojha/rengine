<script lang="ts">
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Download from '@lucide/svelte/icons/download';
	import Zap from '@lucide/svelte/icons/zap';
	import X from '@lucide/svelte/icons/x';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Keyboard from '@lucide/svelte/icons/keyboard';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Spinner } from '$lib/components/ui/spinner';
	import { isLive } from '$lib/config/exports';
	import { exportsStore } from '$lib/stores/exports.svelte';
	import ExportMenuItems from '../export-menu-items.svelte';
	import ExportsSheet from '../exports-sheet.svelte';
	import TripwireButton from '$lib/components/tripwires/tripwire-button.svelte';
	import SortMenu from './sort-menu.svelte';
	import { asDensity, type Density, type SortOption, type TableColumn } from './columns';
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
		density: Density;
		onDensity: (d: Density) => void;
		refreshing: boolean;
		onRefresh: () => void;
		projectId?: string;
		scanId?: string;
		exportFilters?: Record<string, unknown>;
		showGroupBy?: boolean;
		showColumns?: boolean;
		columnsLocked?: boolean;
		/** opens the table's keyboard shortcuts */
		onShortcuts?: () => void;
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
		columnsLocked = false,
		onShortcuts
	}: Props = $props();

	// one target per scan
	let groupDimensions = $derived(
		scanId ? dimensions.filter((d) => d.key !== 'target') : dimensions
	);
	let groupLabel = $derived(groupDimensions.find((d) => d.key === groupBy)?.label ?? '');
	let offersGroup = $derived(showGroupBy && groupDimensions.length > 0);
	let offersColumns = $derived(showColumns && !columnsLocked && !groupBy);
	let viewLabel = $derived(groupBy ? groupLabel : 'View');
	let exportQuery = $derived(typeof exportFilters.q === 'string' ? exportFilters.q : '');
	let exporting = $derived(exportsStore.rows.some((row) => isLive(row.status)));

	let moreRef = $state<HTMLElement | null>(null);
	let tripwireOpen = $state(false);
	let historyOpen = $state(false);
	let pending = $state(false);
	let withEvidence = $state(false);
</script>

{#if !groupBy}
	<SortMenu {sorts} {sortKey} {sortDir} {onSort} />
{/if}

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
								size="sm"
								class={groupBy ? 'border-primary/50 bg-primary/5' : ''}
								aria-label={groupBy ? `View, grouped by ${groupLabel}` : 'View'}
							>
								<SlidersHorizontal class="size-4" />
								<span class="hidden sm:inline">{viewLabel}</span>
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content
				>{groupBy ? `Grouped by ${groupLabel}` : 'Group, columns and density'}</Tooltip.Content
			>
		</Tooltip.Root>
		<DropdownMenu.Content align="end" class="w-56">
			{#if offersGroup}
				<DropdownMenu.Group>
					<DropdownMenu.Label>Group by</DropdownMenu.Label>
					<DropdownMenu.RadioGroup value={groupBy} onValueChange={onGroupBy}>
						<DropdownMenu.RadioItem value="">No grouping</DropdownMenu.RadioItem>
						{#each groupDimensions as groupDimension (groupDimension.key)}
							<DropdownMenu.RadioItem value={groupDimension.key}>
								{groupDimension.label}
							</DropdownMenu.RadioItem>
						{/each}
					</DropdownMenu.RadioGroup>
				</DropdownMenu.Group>
			{/if}
			{#if offersColumns}
				{#if offersGroup}<DropdownMenu.Separator />{/if}
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
			{/if}
			{#if offersGroup || offersColumns}<DropdownMenu.Separator />{/if}
			<DropdownMenu.Group>
				<DropdownMenu.Label>Density</DropdownMenu.Label>
				<DropdownMenu.RadioGroup value={density} onValueChange={(v) => onDensity(asDensity(v))}>
					<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
					<DropdownMenu.RadioItem value="cozy">Comfortable</DropdownMenu.RadioItem>
				</DropdownMenu.RadioGroup>
			</DropdownMenu.Group>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
	{#if groupBy}
		<Button
			variant="outline"
			size="icon-sm"
			class="border-primary/50 bg-primary/5 text-muted-foreground hover:text-foreground"
			aria-label="Clear grouping"
			onclick={() => onGroupBy('')}
		>
			<X class="size-4" />
		</Button>
	{/if}
</ButtonGroup>

<DropdownMenu.Root>
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props: tip })}
				<DropdownMenu.Trigger {...tip}>
					{#snippet child({ props })}
						<Button
							{...props}
							bind:ref={moreRef}
							variant="outline"
							size="icon-sm"
							aria-label="More"
						>
							{#if pending || exporting || refreshing}
								<Spinner class="size-4" />
							{:else}
								<Ellipsis class="size-4" />
							{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content>Export, tripwire, refresh</Tooltip.Content>
	</Tooltip.Root>
	<DropdownMenu.Content align="end" class="w-52">
		<DropdownMenu.Sub>
			<DropdownMenu.SubTrigger disabled={!projectId}>
				<Download class="size-4" />
				Export
			</DropdownMenu.SubTrigger>
			<DropdownMenu.SubContent class="w-48">
				<ExportMenuItems
					{dimension}
					{projectId}
					{scanId}
					filters={exportFilters}
					onHistory={() => (historyOpen = true)}
					onPending={(value) => (pending = value)}
					bind:withEvidence
				/>
			</DropdownMenu.SubContent>
		</DropdownMenu.Sub>
		<DropdownMenu.Item onSelect={() => setTimeout(() => (tripwireOpen = true), 0)}>
			<Zap class="size-4" />
			Tripwire on this query
		</DropdownMenu.Item>
		<DropdownMenu.Separator />
		<DropdownMenu.Item onSelect={() => onRefresh()} disabled={refreshing}>
			<RefreshCw class="size-4" />
			Refresh
		</DropdownMenu.Item>
		{#if onShortcuts}
			<DropdownMenu.Item onSelect={() => onShortcuts()}>
				<Keyboard class="size-4" />
				Keyboard shortcuts
				<DropdownMenu.Shortcut><Kbd>?</Kbd></DropdownMenu.Shortcut>
			</DropdownMenu.Item>
		{/if}
	</DropdownMenu.Content>
</DropdownMenu.Root>

<TripwireButton
	{dimension}
	{projectId}
	scanId={scanId || null}
	query={exportQuery}
	anchor={moreRef}
	bind:open={tripwireOpen}
/>
<ExportsSheet bind:open={historyOpen} {projectId} {scanId} />
