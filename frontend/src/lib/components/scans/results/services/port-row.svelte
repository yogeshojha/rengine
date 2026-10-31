<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import PortStrip from './port-strip.svelte';
	import { PortFlag } from '$lib/config/timeline';
	import type { ServicePortRow, TimelineScan } from '$lib/types/timeline';
	import {
		formatDateTime,
		formatDayOrDate,
		formatMonthDay,
		relativeTimeLong
	} from '$lib/utilities/dates';
	import { columnCell, rowTone } from '../table/columns';
	import { PORT_COLUMNS, PORT_LEAD_COLUMNS } from './timeline-columns';

	interface Props {
		row: ServicePortRow;
		scans: TimelineScan[];
		index: number;
		focused: boolean;
		pad: string;
		highlight: number;
		onHover: (index: number) => void;
		/** opens the services of a run narrowed to the port */
		onOpen: (port: number, scanId: string) => void;
	}

	let { row, scans, index, focused, pad, highlight, onHover, onOpen }: Props = $props();

	let tone = $derived(rowTone(false, focused));
	let scanIndex = $derived(new Map(scans.map((s, i) => [s.id, i])));
	let last = $derived(scans.length - 1);
	let isNew = $derived(row.flags.includes(PortFlag.NEW));
	let gone = $derived(row.flags.includes(PortFlag.GONE));

	let firstSeen = $derived(row.first_seen_at ? formatDayOrDate(row.first_seen_at) : '');
	let firstSeenHint = $derived(
		row.first_seen_at
			? `${formatDateTime(row.first_seen_at)} · ${relativeTimeLong(row.first_seen_at)}`
			: null
	);
	let lastChange = $derived.by(() => {
		if (!row.last_change_scan_id) return '';
		const i = scanIndex.get(row.last_change_scan_id);
		if (i === undefined) return '';
		const cell = row.cells[i];
		const at = scans[i].started_at;
		const date = at ? formatMonthDay(at) : '';
		const delta = cell.delta > 0 ? `${cell.delta} more` : `${-cell.delta} fewer`;
		return `${date} · ${delta} ${Math.abs(cell.delta) === 1 ? 'address' : 'addresses'}`;
	});
	let software = $derived([row.service_name, row.product].filter(Boolean).join(' · '));
</script>

<div
	class="group flex cursor-pointer items-center gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-row-index={index}
	aria-label="Open services on port {row.port}"
	onclick={() => onOpen(row.port, scans[last].id)}
	onkeydown={(e) => {
		if (e.target !== e.currentTarget) return;
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(row.port, scans[last].id);
		}
	}}
>
	<div
		class="sticky left-0 z-[1] flex min-w-0 items-baseline gap-2 bg-card pr-2 {PORT_LEAD_COLUMNS[0]
			.width}"
	>
		<span class="font-mono text-sm leading-5 font-medium {gone ? 'text-muted-foreground' : ''}"
			>{row.port}/{row.protocol}</span
		>
		<span class="truncate text-xs text-muted-foreground">{software}</span>
		{#if isNew}
			<span class="rounded-sm border px-1 text-2xs text-muted-foreground">New</span>
		{/if}
	</div>

	{#each PORT_COLUMNS as col (col.key)}
		<div class={columnCell(col)}>
			{#if col.key === 'strip'}
				<PortStrip
					cells={row.cells}
					{scans}
					label="{row.port}/{row.protocol}"
					peak={row.peak}
					{highlight}
					{onHover}
					onPick={(i) => onOpen(row.port, scans[i].id)}
				/>
			{:else if col.key === 'now'}
				<span class="text-xs tabular-nums {row.now ? '' : 'text-muted-foreground'}"
					>{row.now.toLocaleString()}</span
				>
			{:else if col.key === 'first'}
				<Hint text={firstSeenHint}>
					{#snippet child(props)}
						<span {...props} class="truncate text-xs text-muted-foreground tabular-nums"
							>{firstSeen}</span
						>
					{/snippet}
				</Hint>
			{:else if col.key === 'last'}
				<span class="truncate text-xs text-muted-foreground">{lastChange || 'Unchanged'}</span>
			{/if}
		</div>
	{/each}
</div>
