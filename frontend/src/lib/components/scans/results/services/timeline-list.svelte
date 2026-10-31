<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import AddressRow from './address-row.svelte';
	import PortRow from './port-row.svelte';
	import {
		ADDRESS_CELL,
		ADDRESS_FLAG_HELP,
		ADDRESS_LEGEND,
		ADDRESS_STATE_LABELS,
		LANE_CELL,
		LaneState,
		PORT_FLAG_HELP,
		ServiceTimelineMode,
		type AddressFlag,
		type PortFlag
	} from '$lib/config/timeline';
	import type { ServiceTimelineResult } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { columnCell, type TableColumn } from '../table/columns';
	import { CELL_PX, cellLeft, stripWidth } from '../web-assets/timeline-columns';
	import {
		ADDRESS_COLUMNS,
		ADDRESS_LEAD_COLUMNS,
		MATRIX_CELL_PX,
		PORT_COLUMNS,
		PORT_LEAD_COLUMNS
	} from './timeline-columns';

	interface Props {
		result: ServiceTimelineResult;
		loading: boolean;
		focusedIndex: number;
		pad: string;
		flag: AddressFlag | PortFlag | null;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		/** opens the services Timeline of an earlier run */
		onOpenScan: (scanId: string) => void;
		onAddress: (ip: string) => void;
		onOpenService: (serviceId: string, scanId: string) => void;
		onPort: (port: number, scanId: string) => void;
		track: (node: HTMLElement) => void | (() => void);
	}

	let {
		result,
		loading,
		focusedIndex,
		pad,
		flag,
		sortKey,
		sortDir,
		onSort,
		onOpenScan,
		onAddress,
		onOpenService,
		onPort,
		track
	}: Props = $props();

	let byPort = $derived(result.mode === ServiceTimelineMode.PORT);
	let px = $derived(byPort ? MATRIX_CELL_PX : CELL_PX);
	let lead = $derived(byPort ? PORT_LEAD_COLUMNS : ADDRESS_LEAD_COLUMNS);
	let columns = $derived(byPort ? PORT_COLUMNS : ADDRESS_COLUMNS);
	let scans = $derived(result.scans);
	let width = $derived(stripWidth(scans.length, px));
	let last = $derived(scans.length - 1);
	let highlight = $state(-1);
	const expanded = new SvelteSet<string>();

	// the viewed scan, the first scan, then every few columns from the right, each kept clear of the others
	const LABEL_PX = 40;
	let labels = $derived.by(() => {
		const n = scans.length;
		if (!n) return [];
		const every = px > CELL_PX ? (n > 30 ? 4 : 2) : n > 30 ? 8 : n > 8 ? 4 : 2;
		const span = (i: number, align: 'start' | 'center' | 'end'): [number, number] => {
			const x = cellLeft(i, px) + offset(align);
			if (align === 'start') return [x, x + LABEL_PX];
			if (align === 'end') return [x - LABEL_PX, x];
			return [x - LABEL_PX / 2, x + LABEL_PX / 2];
		};
		const placed: { index: number; align: 'start' | 'center' | 'end'; span: [number, number] }[] =
			[];
		const place = (index: number, align: 'start' | 'center' | 'end') => {
			const next = span(index, align);
			if (placed.some((p) => next[0] < p.span[1] + 6 && p.span[0] < next[1] + 6)) return;
			placed.push({ index, align, span: next });
		};
		place(n - 1, 'end');
		if (n > 1) place(0, 'start');
		for (let i = n - 1 - every; i > 0; i -= every) place(i, 'center');
		return placed.sort((a, b) => a.index - b.index);
	});

	function shift(align: 'start' | 'center' | 'end'): string {
		if (align === 'start') return '';
		return align === 'end' ? '-translate-x-full' : '-translate-x-1/2';
	}
	function offset(align: 'start' | 'center' | 'end'): number {
		return align === 'start' ? 0 : align === 'end' ? px : px / 2;
	}
	function scanHint(i: number): string {
		const at = scans[i]?.started_at;
		const when = at ? formatDateTime(at) : '';
		return i === last ? `${when} · This scan` : `${when} · Open this run's services`;
	}
	function toggle(ip: string) {
		if (expanded.has(ip)) expanded.delete(ip);
		else expanded.add(ip);
	}
	let help = $derived(
		flag
			? byPort
				? PORT_FLAG_HELP[flag as PortFlag]
				: ADDRESS_FLAG_HELP[flag as AddressFlag]
			: null
	);
</script>

{#snippet sortable(col: TableColumn)}
	{#if col.sort}
		<button
			type="button"
			class="flex items-center gap-1 rounded-sm uppercase outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/70 {sortKey ===
			col.sort
				? 'text-foreground'
				: ''}"
			onclick={() => onSort(col.sort ?? col.key)}
		>
			{col.label}
			{#if sortKey === col.sort}
				{#if sortDir === 1}<ArrowUp class="size-3" />{:else}<ArrowDown class="size-3" />{/if}
				<span class="sr-only">, sorted {sortDir === 1 ? 'ascending' : 'descending'}</span>
			{/if}
		</button>
	{:else}
		{col.label}
	{/if}
{/snippet}

<ScrollArea orientation="horizontal">
	<div
		class="flex items-end gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
	>
		{#each lead as col (col.key)}
			<div
				class="sticky left-0 z-[1] min-w-0 bg-[color-mix(in_oklch,var(--muted)_20%,var(--card))] pr-2 {col.width}"
			>
				{@render sortable(col)}
			</div>
		{/each}
		{#each columns as col (col.key)}
			<div class={columnCell(col)}>
				{#if col.key === 'strip'}
					<div class="relative h-4 normal-case tabular-nums" style="width: {width}px">
						{#each labels as label (label.index)}
							{@const at = scans[label.index].started_at}
							<Hint text={scanHint(label.index)}>
								{#snippet child(props)}
									<button
										{...props}
										type="button"
										class="absolute bottom-0 rounded-sm whitespace-nowrap outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/70 {shift(
											label.align
										)} {label.index === last || highlight === label.index ? 'text-foreground' : ''}"
										style="left: {cellLeft(label.index, px) + offset(label.align)}px"
										disabled={label.index === last}
										onmouseenter={() => (highlight = label.index)}
										onmouseleave={() => (highlight = -1)}
										onclick={() => onOpenScan(scans[label.index].id)}
									>
										{at ? formatMonthDay(at) : ''}
									</button>
								{/snippet}
							</Hint>
						{/each}
					</div>
				{:else}
					{@render sortable(col)}
				{/if}
			</div>
		{/each}
	</div>

	<div
		class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}"
		{@attach track}
	>
		{#if byPort}
			{#each result.ports as row, i (`${row.port}/${row.protocol}`)}
				<PortRow
					{row}
					{scans}
					index={i}
					focused={focusedIndex === i}
					{pad}
					{highlight}
					onHover={(col) => (highlight = col)}
					onOpen={onPort}
				/>
			{/each}
		{:else}
			{#each result.addresses as row, i (row.ip)}
				<AddressRow
					{row}
					{scans}
					index={i}
					focused={focusedIndex === i}
					expanded={expanded.has(row.ip)}
					{pad}
					{highlight}
					onHover={(col) => (highlight = col)}
					onToggle={toggle}
					{onAddress}
					{onOpenService}
				/>
			{/each}
		{/if}
	</div>
</ScrollArea>

<div
	class="flex flex-wrap items-center gap-x-1 gap-y-1 border-t px-2 py-1.5 text-xs text-muted-foreground"
>
	{#if byPort}
		<span class="flex items-center gap-1.5 px-2 py-1">
			<span class="h-3 w-3 rounded-[3px] bg-fill-muted/50" aria-hidden="true"></span>
			<span class="h-3 w-3 rounded-[3px] bg-fill-muted" aria-hidden="true"></span>
			<span class="h-3 w-3 rounded-[3px] bg-fill-strong" aria-hidden="true"></span>
			Addresses with the port open, fewer to more
		</span>
		<span class="flex items-center gap-1.5 px-2 py-1">
			<span
				class="h-3 w-3 rounded-[3px] bg-fill-muted outline-2 outline-offset-[-2px] outline-foreground outline"
				aria-hidden="true"
			></span>
			More addresses than the run before
		</span>
		<span class="flex items-center gap-1.5 px-2 py-1">
			<span
				class="h-3 w-3 rounded-[3px] bg-fill-muted outline-2 outline-offset-[-2px] outline-foreground outline-dashed"
				aria-hidden="true"
			></span>
			Fewer
		</span>
		<span class="flex items-center gap-1.5 px-2 py-1">
			<span class="h-3 w-3 rounded-[3px] {ADDRESS_CELL.unobserved}" aria-hidden="true"></span>
			Ports not scanned
		</span>
	{:else}
		{#each ADDRESS_LEGEND as state (state)}
			<span class="flex items-center gap-1.5 px-2 py-1">
				<span class="h-3 w-2.5 shrink-0 rounded-[2px] {ADDRESS_CELL[state]}" aria-hidden="true"
				></span>
				{ADDRESS_STATE_LABELS[state]}
			</span>
		{/each}
		<span class="flex items-center gap-1.5 px-2 py-1">
			<span class="relative h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-muted/50" aria-hidden="true">
				<span
					class="absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground ring-1 ring-card"
				></span>
			</span>
			Software changed
		</span>
		<span class="ml-3 flex items-center gap-1.5 px-2 py-1">
			<span
				class="h-2.5 w-2.5 shrink-0 rounded-[2px] {LANE_CELL[LaneState.OPEN]}"
				aria-hidden="true"
			></span>
			Port open
		</span>
		<span class="flex items-center gap-1.5 px-2 py-1">
			<span
				class="h-2.5 w-2.5 shrink-0 rounded-[2px] {LANE_CELL[LaneState.CLOSED]}"
				aria-hidden="true"
			></span>
			Port closed
		</span>
	{/if}
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span
			class="h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-muted outline outline-offset-1 outline-foreground/70"
			aria-hidden="true"
		></span>
		This scan
	</span>
	{#if help}
		<span class="ml-auto px-2 py-1">{help}</span>
	{/if}
</div>
