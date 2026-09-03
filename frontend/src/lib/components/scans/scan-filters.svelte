<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import ListFilter from '@lucide/svelte/icons/list-filter';
	import CalendarRange from '@lucide/svelte/icons/calendar-range';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { SCAN_TIME_RANGES, type ScanTimeRange } from '$lib/types/scan';
	import type { ScanFacet } from '$lib/types/scan';
	import type { ScheduleMode } from '$lib/stores/scans.svelte';

	const SCHEDULE_MODES: { key: ScheduleMode; label: string }[] = [
		{ key: 'all', label: 'All scans' },
		{ key: 'scheduled', label: 'Scheduled only' },
		{ key: 'manual', label: 'Manual only' }
	];

	interface Props {
		search: string;
		onSearchChange: (q: string) => void;
		engines: string[];
		engineOptions: ScanFacet[];
		onToggleEngine: (name: string) => void;
		contexts: string[];
		contextOptions: ScanFacet[];
		onToggleContext: (name: string) => void;
		timeRange: ScanTimeRange;
		onTimeRange: (range: ScanTimeRange) => void;
		scheduleMode: ScheduleMode;
		onScheduleMode: (mode: ScheduleMode) => void;
	}

	let {
		search,
		onSearchChange,
		engines,
		engineOptions,
		onToggleEngine,
		contexts,
		contextOptions,
		onToggleContext,
		timeRange,
		onTimeRange,
		scheduleMode,
		onScheduleMode
	}: Props = $props();

	let rangeLabel = $derived(SCAN_TIME_RANGES.find((r) => r.key === timeRange)?.label ?? 'All time');
	let scheduleModeLabel = $derived(
		SCHEDULE_MODES.find((m) => m.key === scheduleMode)?.label ?? 'All scans'
	);
</script>

<div class="flex flex-wrap items-center gap-2">
	<div class="relative min-w-[180px] flex-1 sm:max-w-xs">
		<Search class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
		<Input
			type="text"
			placeholder="Search target, engine, context…"
			class="h-9 pl-9"
			value={search}
			oninput={(e) => onSearchChange(e.currentTarget.value)}
		/>
		{#if search}
			<Button
				variant="ghost"
				size="icon"
				class="absolute top-1/2 right-1 h-6 w-6 -translate-y-1/2"
				aria-label="Clear search"
				onclick={() => onSearchChange('')}
			>
				<X class="h-3 w-3" />
			</Button>
		{/if}
	</div>

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
			<DropdownMenu.Content align="start" class="max-h-none overflow-visible">
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
					{#each engineOptions as e (e.name)}
						<DropdownMenu.CheckboxItem
							checked={engines.includes(e.name)}
							onCheckedChange={() => onToggleEngine(e.name)}
						>
							<span class="flex-1 truncate">{e.name}</span>
							<span class="ml-3 tabular-nums text-muted-foreground">{e.count}</span>
						</DropdownMenu.CheckboxItem>
					{/each}
				</ScrollArea>
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
			<DropdownMenu.Content align="start" class="max-h-none overflow-visible">
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
					{#each contextOptions as c (c.name)}
						<DropdownMenu.CheckboxItem
							checked={contexts.includes(c.name)}
							onCheckedChange={() => onToggleContext(c.name)}
						>
							<span class="flex-1 truncate">{c.name}</span>
							<span class="ml-3 tabular-nums text-muted-foreground">{c.count}</span>
						</DropdownMenu.CheckboxItem>
					{/each}
				</ScrollArea>
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

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					size="sm"
					class="h-9 gap-2 {scheduleMode !== 'all' ? 'border-primary/50 bg-primary/5' : ''}"
				>
					<CalendarClock class="h-4 w-4" />
					<span class="hidden sm:inline">{scheduleModeLabel}</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="start">
			{#each SCHEDULE_MODES as m (m.key)}
				<DropdownMenu.CheckboxItem
					checked={scheduleMode === m.key}
					onCheckedChange={() => onScheduleMode(m.key)}
				>
					{m.label}
				</DropdownMenu.CheckboxItem>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</div>
