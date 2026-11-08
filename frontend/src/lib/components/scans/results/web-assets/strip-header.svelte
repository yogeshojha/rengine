<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import Hint from '$lib/components/hint.svelte';
	import type { TimelineScan } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { columnCell, type TableColumn } from '../table/columns';
	import { cellLeft, stripWidth } from './timeline-columns';

	type Align = 'start' | 'center' | 'end';

	interface Props {
		leadColumns: TableColumn[];
		columns: TableColumn[];
		scans: TimelineScan[];
		sortKey: string;
		sortDir: 1 | -1;
		/** the hint on an earlier scan's date label */
		openLabel: string;
		highlight: number;
		onSort: (key: string) => void;
		onOpenScan: (scanId: string) => void;
	}

	let {
		leadColumns,
		columns,
		scans,
		sortKey,
		sortDir,
		openLabel,
		highlight = $bindable(),
		onSort,
		onOpenScan
	}: Props = $props();

	const LABEL_PX = 40;
	let width = $derived(stripWidth(scans.length));
	let last = $derived(scans.length - 1);

	let labels = $derived.by(() => {
		const n = scans.length;
		if (!n) return [];
		const every = n > 30 ? 8 : n > 8 ? 4 : 2;
		const span = (i: number, align: Align): [number, number] => {
			const x = cellLeft(i) + offset(align);
			if (align === 'start') return [x, x + LABEL_PX];
			if (align === 'end') return [x - LABEL_PX, x];
			return [x - LABEL_PX / 2, x + LABEL_PX / 2];
		};
		const placed: { index: number; align: Align; span: [number, number] }[] = [];
		const place = (index: number, align: Align) => {
			const next = span(index, align);
			if (placed.some((p) => next[0] < p.span[1] + 6 && p.span[0] < next[1] + 6)) return;
			placed.push({ index, align, span: next });
		};
		place(n - 1, 'end');
		if (n > 1) place(0, 'start');
		for (let i = n - 1 - every; i > 0; i -= every) place(i, 'center');
		return placed.sort((a, b) => a.index - b.index);
	});

	function shift(align: Align): string {
		if (align === 'start') return '';
		return align === 'end' ? '-translate-x-full' : '-translate-x-1/2';
	}
	function offset(align: Align): number {
		return align === 'start' ? 0 : align === 'end' ? 10 : 5;
	}
	function scanHint(i: number): string {
		const at = scans[i]?.started_at;
		const when = at ? formatDateTime(at) : '';
		return i === last ? `${when} · This scan` : `${when} · ${openLabel}`;
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

<div
	class="flex items-end gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
>
	{#each leadColumns as col (col.key)}
		<div class="min-w-0 {col.width}">{@render sortable(col)}</div>
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
