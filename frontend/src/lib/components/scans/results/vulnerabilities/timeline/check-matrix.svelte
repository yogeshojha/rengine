<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import { CHECK_CELL, CheckState } from '$lib/config/timeline';
	import { SEVERITY_FILL, Severity } from '$lib/config/vulnerabilities';
	import { plural } from '$lib/utilities/strings';
	import type { CheckRow as CheckRowRead, FindingTimelineResult } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { CELL_GAP_PX, cellLeft, stripWidth } from '../../web-assets/timeline-columns';
	import { MATRIX_CELL_PX } from '../../services/timeline-columns';
	import CheckRow from './check-row.svelte';
	import { CHECK_PX, HOSTS_PX } from './columns';

	interface Props {
		result: FindingTimelineResult;
		loading: boolean;
		focusedIndex: number;
		pad: string;
		onOpen: (templateId: string) => void;
		/** opens the findings Timeline of an earlier run */
		onOpenScan: (scanId: string) => void;
		track: (node: HTMLElement) => void | (() => void);
	}

	let { result, loading, focusedIndex, pad, onOpen, onOpenScan, track }: Props = $props();

	let scans = $derived(result.scans);
	let n = $derived(scans.length);
	let last = $derived(n - 1);
	let width = $derived(stripWidth(n, MATRIX_CELL_PX));
	let highlight = $state(-1);
	let stats = $derived(result.check_stats);
	let windowNote = $derived(
		result.runs > n && scans[0]?.started_at
			? `Last ${n} of ${result.runs} runs · earlier runs open from ${formatMonthDay(scans[0].started_at)}`
			: ''
	);

	const LABEL_PX = 40;
	let labels = $derived.by(() => {
		if (!n) return [];
		const step = MATRIX_CELL_PX + CELL_GAP_PX;
		const every = Math.max(2, Math.ceil((LABEL_PX + 8) / step));
		const out: { index: number; align: 'start' | 'center' | 'end' }[] = [
			{ index: last, align: 'end' }
		];
		for (let i = last - every; i > every / 2; i -= every) out.push({ index: i, align: 'center' });
		if (n > 1) out.push({ index: 0, align: 'start' });
		return out.sort((a, b) => a.index - b.index);
	});
	function offset(align: 'start' | 'center' | 'end'): number {
		return align === 'start' ? 0 : align === 'end' ? MATRIX_CELL_PX : MATRIX_CELL_PX / 2;
	}
	function shift(align: 'start' | 'center' | 'end'): string {
		if (align === 'start') return '';
		return align === 'end' ? '-translate-x-full' : '-translate-x-1/2';
	}
	function scanHint(i: number): string {
		const at = scans[i]?.started_at;
		const when = at ? formatDateTime(at) : '';
		return i === last ? `${when} · This scan` : `${when} · Open this run's findings`;
	}
	function key(row: CheckRowRead): string {
		return row.template_id;
	}
</script>

{#snippet stat(label: string, value: string, detail: string)}
	<div class="flex min-w-0 flex-col gap-0.5">
		<span class="text-2xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
		<span class="text-2xl leading-none font-semibold tracking-tight tabular-nums">{value}</span>
		<span class="truncate text-xs text-muted-foreground">{detail}</span>
	</div>
{/snippet}

{#if stats}
	<div class="flex flex-wrap gap-7 border-b px-5 py-4">
		{@render stat(
			'Checks found',
			String(stats.checks),
			[
				`in the last ${plural(n, 'run')}`,
				stats.tested_checks == null ? '' : `of ${stats.tested_checks.toLocaleString()} tested`
			]
				.filter(Boolean)
				.join(' · ')
		)}
		{@render stat(
			'Spread',
			String(stats.spread),
			stats.spread ? 'on more web assets than when first found' : ''
		)}
		{@render stat('Shrank', String(stats.shrank), stats.shrank ? 'fewer web assets' : '')}
		{@render stat('Cleared', String(stats.cleared), stats.cleared ? 'no web asset left' : '')}
		{@render stat(
			'New to the library',
			String(stats.library_new),
			stats.library_new ? 'added inside the window' : ''
		)}
	</div>
{/if}

<ScrollArea orientation="horizontal">
	<div
		class="flex items-end gap-6 border-b bg-muted/20 py-2 pr-4 pl-4 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
	>
		<div
			class="sticky left-0 z-[1] shrink-0 bg-[color-mix(in_oklch,var(--muted)_20%,var(--card))] pr-2"
			style="width: {CHECK_PX}px"
		>
			Check
		</div>
		<div class="relative h-4 shrink-0 normal-case tabular-nums" style="width: {width}px">
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
							style="left: {cellLeft(label.index, MATRIX_CELL_PX) + offset(label.align)}px"
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
		<div class="ml-auto shrink-0 text-right" style="width: {HOSTS_PX}px">Hosts now</div>
	</div>

	<div
		class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}"
		role="rowgroup"
		{@attach track}
	>
		{#each result.checks as row, i (key(row))}
			<CheckRow
				{row}
				{scans}
				index={i}
				focused={focusedIndex === i}
				{pad}
				{highlight}
				onHover={(col) => (highlight = col)}
				{onOpen}
				{onOpenScan}
			/>
		{/each}
	</div>
</ScrollArea>

<div
	class="flex flex-wrap items-center gap-x-1 gap-y-1 border-t px-2 py-1.5 text-xs text-muted-foreground"
>
	<span class="flex items-center gap-1.5 px-2 py-1">
		{#each [45, 70, 100] as share (share)}
			<span
				class="h-3 w-3 rounded-[3px]"
				style="background: color-mix(in oklch, {SEVERITY_FILL[
					Severity.HIGH
				]} {share}%, var(--card))"
				aria-hidden="true"
			></span>
		{/each}
		Fewer to more web assets, in the check's severity
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span
			class="h-3 w-3 rounded-[3px] bg-fill-muted outline-2 outline-offset-[-2px] outline-foreground outline"
			aria-hidden="true"
		></span>
		More than the run before
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span
			class="h-3 w-3 rounded-[3px] bg-fill-muted outline-2 outline-offset-[-2px] outline-foreground outline-dashed"
			aria-hidden="true"
		></span>
		Fewer
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="h-3 w-3 rounded-[3px] {CHECK_CELL[CheckState.NOT_IN_LIBRARY]}" aria-hidden="true"
		></span>
		Check not in the library yet
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="h-3 w-3 rounded-[3px] {CHECK_CELL[CheckState.NOT_TESTED]}" aria-hidden="true"
		></span>
		Not tested
	</span>
	<span class="ml-auto flex flex-wrap items-center gap-x-3 px-2 py-1">
		{#if windowNote}<span>{windowNote}</span>{/if}
		<span>A cell lists the web assets that gained or lost the finding in that run</span>
	</span>
</div>
