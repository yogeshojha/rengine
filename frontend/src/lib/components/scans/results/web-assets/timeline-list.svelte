<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import TimelineRow from './timeline-row.svelte';
	import {
		FLAG_HELP,
		LEGEND_STATES,
		STATE_CELL,
		STATE_QUERY,
		WEB_STATE_LABELS,
		WebAssetState,
		type TimelineFlag
	} from '$lib/config/timeline';
	import type { TimelineSearchResult } from '$lib/types/timeline';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { columnCell, type TableColumn } from '../table/columns';
	import {
		cellLeft,
		stripWidth,
		TIMELINE_COLUMNS,
		TIMELINE_LEAD_COLUMNS
	} from './timeline-columns';

	interface Props {
		result: TimelineSearchResult;
		loading: boolean;
		apex?: string;
		selectedId: string | null;
		focusedIndex: number;
		pad: string;
		flag: TimelineFlag | null;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		onOpen: (s: SubdomainRead) => void;
		onOpenAt: (s: SubdomainRead, scanId: string) => void;
		/** opens the Timeline of an earlier run */
		onOpenScan: (scanId: string) => void;
		onQuery: (token: string) => void;
		onGone: () => void;
		track: (node: HTMLElement) => void | (() => void);
	}

	let {
		result,
		loading,
		apex = '',
		selectedId,
		focusedIndex,
		pad,
		flag,
		sortKey,
		sortDir,
		onSort,
		onOpen,
		onOpenAt,
		onOpenScan,
		onQuery,
		onGone,
		track
	}: Props = $props();

	let scans = $derived(result.scans);
	let width = $derived(stripWidth(scans.length));
	let last = $derived(scans.length - 1);
	let highlight = $state(-1);
	let windowNote = $derived(
		result.runs > scans.length && scans[0]?.started_at
			? `Last ${scans.length} of ${result.runs} runs · earlier runs open from ${formatMonthDay(scans[0].started_at)}`
			: ''
	);

	// the viewed scan, the first scan, then every few columns from the right, each kept clear of the others
	const LABEL_PX = 40;
	let labels = $derived.by(() => {
		const n = scans.length;
		if (!n) return [];
		const every = n > 30 ? 8 : n > 8 ? 4 : 2;
		const span = (i: number, align: 'start' | 'center' | 'end'): [number, number] => {
			const x = cellLeft(i) + offset(align);
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
		return align === 'start' ? 0 : align === 'end' ? 10 : 5;
	}
	function scanHint(i: number): string {
		const at = scans[i]?.started_at;
		const when = at ? formatDateTime(at) : '';
		return i === last ? `${when} · This scan` : `${when} · Open this run's Timeline`;
	}
	function legendPick(state: WebAssetState) {
		if (state === WebAssetState.GONE) return onGone();
		const token = STATE_QUERY[state];
		if (token) onQuery(token);
	}
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
		{#each TIMELINE_LEAD_COLUMNS as col (col.key)}
			<div class="min-w-0 {col.width}">{@render sortable(col)}</div>
		{/each}
		{#each TIMELINE_COLUMNS as col (col.key)}
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
										style="left: {cellLeft(label.index) + offset(label.align)}px"
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
		{#each result.items as row, i (row.host.id)}
			<TimelineRow
				{row}
				{scans}
				index={i}
				{apex}
				selected={selectedId === row.host.id}
				focused={focusedIndex === i}
				{pad}
				{highlight}
				onHover={(col) => (highlight = col)}
				{onOpen}
				{onOpenAt}
			/>
		{/each}
	</div>
</ScrollArea>

<div
	class="flex flex-wrap items-center gap-x-1 gap-y-1 border-t px-2 py-1.5 text-xs text-muted-foreground"
>
	{#each LEGEND_STATES as state (state)}
		{@const filters = state === WebAssetState.GONE || !!STATE_QUERY[state]}
		<button
			type="button"
			class="flex items-center gap-1.5 rounded-md px-2 py-1 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/70 {filters
				? 'hover:bg-muted hover:text-foreground'
				: 'cursor-default'}"
			disabled={!filters}
			aria-label={filters ? `Show ${WEB_STATE_LABELS[state].toLowerCase()} web assets` : undefined}
			onclick={() => legendPick(state)}
		>
			<span
				class="h-3 w-2.5 shrink-0 rounded-[2px] {STATE_CELL[state] || 'border border-border'}"
				aria-hidden="true"
			></span>
			{WEB_STATE_LABELS[state]}
		</button>
	{/each}
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="relative h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-success" aria-hidden="true">
			<span
				class="absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground ring-1 ring-card"
			></span>
		</span>
		Attribute changed
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span
			class="h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-success outline outline-offset-1 outline-foreground/70"
			aria-hidden="true"
		></span>
		This scan
	</span>
	<span class="ml-auto flex flex-wrap items-center gap-x-3 px-2 py-1">
		{#if windowNote}<span>{windowNote}</span>{/if}
		{#if flag}<span>{FLAG_HELP[flag]}</span>{/if}
	</span>
</div>
