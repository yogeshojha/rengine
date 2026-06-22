<script lang="ts">
	import { Search, X, ListFilter, CalendarRange } from 'lucide-svelte';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import {
		SCAN_STATUSES,
		SCAN_TIME_RANGES,
		type ScanStatus,
		type ScanTimeRange
	} from '$lib/types/scan';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import type { ScanFacet, ScanStatusCounts } from '$lib/types/scan';

	interface Props {
		search: string;
		onSearchChange: (q: string) => void;
		statuses: ScanStatus[];
		statusCounts?: ScanStatusCounts | null;
		onToggleStatus: (s: ScanStatus) => void;
		engines: string[];
		engineOptions: ScanFacet[];
		onToggleEngine: (name: string) => void;
		contexts: string[];
		contextOptions: ScanFacet[];
		onToggleContext: (name: string) => void;
		timeRange: ScanTimeRange;
		onTimeRange: (range: ScanTimeRange) => void;
	}

	let {
		search,
		onSearchChange,
		statuses,
		statusCounts = null,
		onToggleStatus,
		engines,
		engineOptions,
		onToggleEngine,
		contexts,
		contextOptions,
		onToggleContext,
		timeRange,
		onTimeRange
	}: Props = $props();

	let rangeLabel = $derived(SCAN_TIME_RANGES.find((r) => r.key === timeRange)?.label ?? 'All time');
</script>

<div class="flex flex-wrap items-center gap-3 gap-y-2">
	<div class="relative flex-1 min-w-0 sm:max-w-sm">
		<Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
		<Input
			type="text"
			placeholder="Search target, engine, context..."
			class="pl-9 h-9"
			value={search}
			oninput={(e) => onSearchChange(e.currentTarget.value)}
		/>
		{#if search}
			<Button
				variant="ghost"
				size="icon"
				class="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
				onclick={() => onSearchChange('')}
			>
				<X class="h-3 w-3" />
			</Button>
		{/if}
	</div>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					size="sm"
					class="h-9 gap-2 {statuses.length > 0 ? 'border-primary/50 bg-primary/5' : ''}"
				>
					<ListFilter class="h-4 w-4" /> Status
					{#if statuses.length}
						<Badge variant="secondary" class="h-5 px-1.5 text-xs">{statuses.length}</Badge>
					{/if}
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="start">
			{#each SCAN_STATUSES as s (s)}
				<DropdownMenu.CheckboxItem
					checked={statuses.includes(s)}
					onCheckedChange={() => onToggleStatus(s)}
				>
					<span class="flex-1">{SCAN_STATUS_LABEL[s]}</span>
					{#if statusCounts}
						<span class="ml-3 tabular-nums text-muted-foreground">{statusCounts[s]}</span>
					{/if}
				</DropdownMenu.CheckboxItem>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	{#if engineOptions.length > 0}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="outline"
						size="sm"
						class="h-9 gap-2 {engines.length > 0 ? 'border-primary/50 bg-primary/5' : ''}"
						disabled={engineOptions.length < 2}
						title={engineOptions.length < 2 ? 'Only one engine in use' : undefined}
					>
						<ListFilter class="h-4 w-4" /> Engine
						{#if engines.length}
							<Badge variant="secondary" class="h-5 px-1.5 text-xs">{engines.length}</Badge>
						{/if}
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start" class="max-h-72 overflow-y-auto">
				{#each engineOptions as e (e.name)}
					<DropdownMenu.CheckboxItem
						checked={engines.includes(e.name)}
						onCheckedChange={() => onToggleEngine(e.name)}
					>
						<span class="flex-1 truncate">{e.name}</span>
						<span class="ml-3 tabular-nums text-muted-foreground">{e.count}</span>
					</DropdownMenu.CheckboxItem>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	{/if}

	{#if contextOptions.length > 0}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="outline"
						size="sm"
						class="h-9 gap-2 {contexts.length > 0 ? 'border-primary/50 bg-primary/5' : ''}"
					>
						<ListFilter class="h-4 w-4" /> Context
						{#if contexts.length}
							<Badge variant="secondary" class="h-5 px-1.5 text-xs">{contexts.length}</Badge>
						{/if}
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start" class="max-h-72 overflow-y-auto">
				{#each contextOptions as c (c.name)}
					<DropdownMenu.CheckboxItem
						checked={contexts.includes(c.name)}
						onCheckedChange={() => onToggleContext(c.name)}
					>
						<span class="flex-1 truncate">{c.name}</span>
						<span class="ml-3 tabular-nums text-muted-foreground">{c.count}</span>
					</DropdownMenu.CheckboxItem>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	{/if}

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					size="sm"
					class="h-9 gap-2 {timeRange !== 'all' ? 'border-primary/50 bg-primary/5' : ''}"
				>
					<CalendarRange class="h-4 w-4" />
					<span class="hidden sm:inline">{rangeLabel}</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="start">
			{#each SCAN_TIME_RANGES as r (r.key)}
				<DropdownMenu.CheckboxItem
					checked={timeRange === r.key}
					onCheckedChange={() => onTimeRange(r.key)}
				>
					{r.label}
				</DropdownMenu.CheckboxItem>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</div>
