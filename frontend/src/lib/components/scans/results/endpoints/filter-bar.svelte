<script lang="ts">
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Layers from '@lucide/svelte/icons/layers';
	import Network from '@lucide/svelte/icons/network';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import ChevronsDownUp from '@lucide/svelte/icons/chevrons-down-up';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import SortMenu from '../table/sort-menu.svelte';
	import type { SortOption, TableColumn } from '../table/columns';
	import type { QueryGroupSpec } from '$lib/types/asset-query';
	import { EndpointSource } from '$lib/config/endpoints';
	import type { EndpointFacetSet, EndpointQuery, EndpointView } from '$lib/utilities/endpoints';

	interface Props {
		query: EndpointQuery;
		facets: EndpointFacetSet;
		onQuery: (q: EndpointQuery) => void;
		dimensions: QueryGroupSpec[];
		columns: TableColumn[];
		visible: string[];
		onToggleColumn: (key: string) => void;
		density: string;
		onDensity: (d: string) => void;
		sorts: SortOption[];
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		refreshing: boolean;
		onRefresh: () => void;
		groupBy: string;
		onGroupBy: (key: string) => void;
		view: EndpointView;
		onView: (v: EndpointView) => void;
		inHost?: boolean;
		hideStatic: boolean;
		onHideStatic: (v: boolean) => void;
		hideRootOnly?: boolean;
		onHideRootOnly?: (v: boolean) => void;
		expandedCount?: number;
		onCollapseAll?: () => void;
		goneCount?: number;
		goneLens?: boolean;
		onGoneLens?: (on: boolean) => void;
	}

	let {
		query,
		facets,
		onQuery,
		dimensions,
		columns,
		visible,
		onToggleColumn,
		density,
		onDensity,
		sorts,
		sortKey,
		sortDir,
		onSort,
		refreshing,
		onRefresh,
		groupBy,
		onGroupBy,
		view,
		onView,
		inHost = false,
		hideStatic,
		onHideStatic,
		hideRootOnly = false,
		onHideRootOnly,
		expandedCount = 0,
		onCollapseAll,
		goneCount = 0,
		goneLens = false,
		onGoneLens
	}: Props = $props();

	const LENSES: { value: EndpointView; label: string; hint: string; icon: typeof Network }[] = [
		{
			value: 'hosts',
			label: 'Hosts',
			hint: 'Every host, ranked',
			icon: Network
		},
		{
			value: 'merged',
			label: 'Across hosts',
			hint: 'Paths merged across hosts',
			icon: Layers
		},
		{ value: 'list', label: 'List', hint: 'One flat list', icon: Rows3 }
	];

	let groupLabel = $derived(dimensions.find((d) => d.key === groupBy)?.label ?? 'Group');
	let hasProxy = $derived(facets.source.some((f) => f.value === EndpointSource.PROXY));
	let hostsAtRest = $derived(view === 'hosts' && !inHost);
	let quickOptions = $derived(
		[
			{ value: 'new', label: 'New' },
			{ value: 'unverified', label: 'Not checked' },
			hasProxy ? { value: 'browsed', label: 'Browsed' } : null,
			hasProxy ? { value: 'unbrowsed', label: 'Not browsed' } : null,
			{ value: 'static', label: 'Hide static' },
			hostsAtRest && onHideRootOnly ? { value: 'rootonly', label: 'Hide root-only' } : null
		].filter((q): q is { value: string; label: string } => q !== null)
	);
	let quick = $derived(
		[
			query.newOnly && 'new',
			query.probed === 'no' && 'unverified',
			query.browsed === 'yes' && 'browsed',
			query.browsed === 'no' && 'unbrowsed',
			hideStatic && 'static',
			hideRootOnly && hostsAtRest && 'rootonly'
		].filter((v): v is string => !!v)
	);

	function setQuick(values: string[]) {
		onQuery({
			...query,
			newOnly: values.includes('new'),
			probed: values.includes('unverified') ? 'no' : 'any',
			browsed: values.includes('browsed') ? 'yes' : values.includes('unbrowsed') ? 'no' : 'any'
		});
		onHideStatic(values.includes('static'));
		if (hostsAtRest) onHideRootOnly?.(values.includes('rootonly'));
	}

	function pick(key: 'source' | 'interest' | 'statusClass', value: string) {
		onQuery({ ...query, [key]: query[key] === value ? '' : value });
	}
</script>

<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
	<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
		{#if facets.source.length > 1}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-9 gap-2 {query.source ? 'border-primary/50 bg-primary/5' : ''}"
						>
							Found by
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-56 overflow-visible">
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
						{#each facets.source as f (f.value)}
							<DropdownMenu.CheckboxItem
								checked={query.source === f.value}
								onCheckedChange={() => pick('source', f.value)}
								closeOnSelect={false}
							>
								<span class="flex-1">{f.label}</span>
								<span class="tabular-nums text-muted-foreground">{f.count}</span>
							</DropdownMenu.CheckboxItem>
						{/each}
					</ScrollArea>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		{#if facets.interest.length}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-9 gap-2 {query.interest ? 'border-primary/50 bg-primary/5' : ''}"
						>
							Interest
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-64 overflow-visible">
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
						{#each facets.interest as f (f.value)}
							<DropdownMenu.CheckboxItem
								checked={query.interest === f.value}
								onCheckedChange={() => pick('interest', f.value)}
								closeOnSelect={false}
							>
								<span class="flex-1">{f.label}</span>
								<span class="tabular-nums text-muted-foreground">{f.count}</span>
							</DropdownMenu.CheckboxItem>
						{/each}
					</ScrollArea>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		{#if facets.status_class.length > 1}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="sm"
							class="h-9 gap-2 {query.statusClass ? 'border-primary/50 bg-primary/5' : ''}"
						>
							Status
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-52 overflow-visible">
					{#each facets.status_class as f (f.value)}
						<DropdownMenu.CheckboxItem
							checked={query.statusClass === f.value}
							onCheckedChange={() => pick('statusClass', f.value)}
							closeOnSelect={false}
						>
							<span class="flex-1">{f.label}</span>
							<span class="tabular-nums text-muted-foreground">{f.count}</span>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}

		<ToggleGroup.Root
			type="multiple"
			value={quick}
			onValueChange={setQuick}
			variant="outline"
			aria-label="Quick filters"
		>
			{#each quickOptions as q (q.value)}
				<ToggleGroup.Item value={q.value} class="h-9 px-3 text-sm font-normal">
					{q.label}
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>

		{#if goneCount > 0 && onGoneLens}
			<Hint text="Endpoints in the previous scan and not in this one">
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<ToggleGroup.Root
							type="single"
							value={goneLens ? 'gone' : ''}
							onValueChange={(v) => onGoneLens(v === 'gone')}
							variant="outline"
							aria-label="Gone since the previous scan"
						>
							<ToggleGroup.Item value="gone" class="h-9 gap-1.5 px-3 text-sm font-normal">
								Gone
								<span class="text-xs tabular-nums text-muted-foreground">
									{goneCount.toLocaleString()}
								</span>
							</ToggleGroup.Item>
						</ToggleGroup.Root>
					</span>
				{/snippet}
			</Hint>
		{/if}
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<ToggleGroup.Root
			type="single"
			value={view}
			onValueChange={(v) => v && onView(v as EndpointView)}
			variant="outline"
			aria-label="View"
		>
			{#each LENSES as lens (lens.value)}
				<Hint text={lens.hint}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<ToggleGroup.Item value={lens.value} class="h-9 gap-1.5 px-3" aria-label={lens.label}>
								<lens.icon class="size-4" />
								<span class="hidden text-sm font-normal lg:inline">{lens.label}</span>
							</ToggleGroup.Item>
						</span>
					{/snippet}
				</Hint>
			{/each}
		</ToggleGroup.Root>

		{#if view !== 'list' && expandedCount > 0 && onCollapseAll}
			<Hint text="Collapse all folders">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon"
						class="h-9 w-9"
						aria-label="Collapse all"
						onclick={onCollapseAll}
					>
						<ChevronsDownUp class="h-4 w-4" />
					</Button>
				{/snippet}
			</Hint>
		{/if}

		{#if dimensions.length && view === 'list'}
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
								{#each dimensions as dimension (dimension.key)}
									<DropdownMenu.RadioItem value={dimension.key}>
										{dimension.label}
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

		<Button
			variant="outline"
			size="icon"
			class="h-9 w-9"
			aria-label="Refresh"
			onclick={onRefresh}
			disabled={refreshing}
		>
			<RefreshCw class="h-4 w-4 {refreshing ? 'animate-spin' : ''}" />
		</Button>
	</div>
</div>
