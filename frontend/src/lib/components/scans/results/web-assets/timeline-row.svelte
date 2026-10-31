<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import TimelineStrip from './timeline-strip.svelte';
	import {
		ABSENT_STATES,
		SILENT_STATES,
		STATE_DOT,
		TimelineFlag,
		WEB_STATE_LABELS,
		WebAssetState
	} from '$lib/config/timeline';
	import type { TimelineRow, TimelineScan } from '$lib/types/timeline';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import {
		formatDateTime,
		formatDayOrDate,
		formatMonthDay,
		relativeTimeLong
	} from '$lib/utilities/dates';
	import Hint from '$lib/components/hint.svelte';
	import { stopProp } from '$lib/utilities';
	import { columnCell, rowTone } from '../table/columns';
	import { TIMELINE_COLUMNS, TIMELINE_LEAD_COLUMNS } from './timeline-columns';

	interface Props {
		row: TimelineRow;
		scans: TimelineScan[];
		index: number;
		apex?: string;
		selected: boolean;
		focused: boolean;
		pad: string;
		highlight: number;
		onHover: (index: number) => void;
		onOpen: (s: SubdomainRead) => void;
		/** opens the host as the run at `scanId` recorded it */
		onOpenAt: (s: SubdomainRead, scanId: string) => void;
	}

	let {
		row,
		scans,
		index,
		apex = '',
		selected,
		focused,
		pad,
		highlight,
		onHover,
		onOpen,
		onOpenAt
	}: Props = $props();

	let host = $derived(row.host);
	let apexSuffix = $derived(
		apex && host.name !== apex && host.name.endsWith(`.${apex}`) ? `.${apex}` : ''
	);
	let headLabels = $derived(
		(apexSuffix ? host.name.slice(0, -apexSuffix.length) : host.name).split('.')
	);
	let tone = $derived(rowTone(selected, focused));
	let isNew = $derived(row.flags.includes(TimelineFlag.NEW));
	let gone = $derived(row.state === WebAssetState.GONE);
	let changes = $derived(row.transitions + row.attribute_changes);

	let scanIndex = $derived(new Map(scans.map((s, i) => [s.id, i])));

	function dateOf(scanId: string | null): string {
		const i = scanId ? scanIndex.get(scanId) : undefined;
		const at = i === undefined ? null : scans[i].started_at;
		return at ? formatMonthDay(at) : '';
	}

	let firstSeen = $derived(row.first_seen_at ? formatDayOrDate(row.first_seen_at) : '');
	let firstSeenHint = $derived(
		row.first_seen_at
			? `${formatDateTime(row.first_seen_at)} · ${relativeTimeLong(row.first_seen_at)}`
			: null
	);

	// the transition the last change made, read off the cells
	let lastChange = $derived.by(() => {
		if (!row.last_change_scan_id) return '';
		const i = scanIndex.get(row.last_change_scan_id);
		if (i === undefined) return '';
		const cell = row.cells[i];
		let before = i - 1;
		while (before >= 0 && SILENT_STATES.has(row.cells[before].state)) before -= 1;
		const prev = before >= 0 ? row.cells[before].state : null;
		const date = dateOf(row.last_change_scan_id);
		if (prev === WebAssetState.UNSEEN) return `${date} · First seen`;
		if (prev && prev !== cell.state) {
			return `${date} · ${WEB_STATE_LABELS[prev]} → ${WEB_STATE_LABELS[cell.state]}`;
		}
		return cell.changed.length ? `${date} · ${cell.changed.join(', ')}` : date;
	});

	function hasRow(i: number): boolean {
		const state = row.cells[i]?.state;
		return !!state && !ABSENT_STATES.has(state) && !SILENT_STATES.has(state);
	}

	// an empty cell opens the newest row
	function pick(i: number) {
		if (hasRow(i)) onOpenAt(host, scans[i].id);
		else onOpen(host);
	}

	function openLastChange(e: Event) {
		stopProp(e);
		if (!row.last_change_scan_id) return;
		const i = scanIndex.get(row.last_change_scan_id);
		if (i !== undefined) pick(i);
	}
</script>

<div
	class="group flex cursor-pointer items-center gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-row-index={index}
	aria-label="Open {host.name}"
	onclick={() => onOpen(host)}
	onkeydown={(e) => {
		if (e.target !== e.currentTarget) return;
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(host);
		}
	}}
>
	<div class="flex min-w-0 items-center {TIMELINE_LEAD_COLUMNS[0].width}">
		<span
			class="min-w-0 font-mono text-sm leading-5 font-medium wrap-anywhere {gone
				? 'text-muted-foreground'
				: ''}"
		>
			{#each headLabels as part, i (i)}{part}{#if i < headLabels.length - 1}.<wbr
					/>{/if}{/each}{#if apexSuffix}<wbr /><span class="font-normal text-muted-foreground"
					>{apexSuffix}</span
				>{/if}
		</span>
	</div>

	{#each TIMELINE_COLUMNS as col (col.key)}
		<div class={columnCell(col)}>
			{#if col.key === 'strip'}
				<TimelineStrip
					cells={row.cells}
					{scans}
					name={host.name}
					{highlight}
					{onHover}
					onPick={pick}
				/>
			{:else if col.key === 'state'}
				<span class="flex min-w-0 items-center gap-1.5 text-xs">
					<span class="size-2 shrink-0 rounded-full {STATE_DOT[row.state]}" aria-hidden="true"
					></span>
					<span class="truncate {gone ? 'text-muted-foreground' : ''}"
						>{WEB_STATE_LABELS[row.state]}</span
					>
					{#if isNew}
						<Badge variant="outline" class="px-1.5 text-2xs">New</Badge>
					{/if}
				</span>
			{:else if col.key === 'first'}
				<Hint text={firstSeenHint}>
					{#snippet child(props)}
						<span {...props} class="truncate text-xs text-muted-foreground tabular-nums"
							>{firstSeen}</span
						>
					{/snippet}
				</Hint>
			{:else if col.key === 'changes'}
				<span class="text-xs tabular-nums {changes ? '' : 'text-muted-foreground'}">
					{changes.toLocaleString()}
				</span>
			{:else if col.key === 'last'}
				{#if lastChange}
					<button
						type="button"
						class="truncate rounded-sm text-left text-xs text-muted-foreground underline-offset-2 outline-none hover:text-foreground hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/70"
						aria-label="Open {host.name} as recorded at its last change"
						onclick={openLastChange}
					>
						{lastChange}
					</button>
				{:else}
					<span class="truncate text-xs text-muted-foreground">Unchanged</span>
				{/if}
			{/if}
		</div>
	{/each}
</div>
