<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Hint from '$lib/components/hint.svelte';
	import AddressStrip from './address-strip.svelte';
	import LaneStrip from './lane-strip.svelte';
	import { AddressFlag } from '$lib/config/timeline';
	import type { ServiceAddressRow, ServiceLane, TimelineScan } from '$lib/types/timeline';
	import {
		formatDateTime,
		formatDayOrDate,
		formatMonthDay,
		relativeTimeLong
	} from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { stopProp } from '$lib/utilities';
	import { columnCell, rowTone } from '../table/columns';
	import { ADDRESS_COLUMNS, ADDRESS_LEAD_COLUMNS } from './timeline-columns';

	interface Props {
		row: ServiceAddressRow;
		scans: TimelineScan[];
		index: number;
		focused: boolean;
		expanded: boolean;
		pad: string;
		highlight: number;
		onHover: (index: number) => void;
		onToggle: (ip: string) => void;
		onAddress: (ip: string) => void;
		/** opens the service as the run recorded it */
		onOpenService: (serviceId: string, scanId: string) => void;
	}

	let {
		row,
		scans,
		index,
		focused,
		expanded,
		pad,
		highlight,
		onHover,
		onToggle,
		onAddress,
		onOpenService
	}: Props = $props();

	const MAX_CHIPS = 8;

	let tone = $derived(rowTone(false, focused));
	let scanIndex = $derived(new Map(scans.map((s, i) => [s.id, i])));
	let isNew = $derived(row.flags.includes(AddressFlag.NEW));

	function dateOf(scanId: string | null): string {
		const i = scanId ? scanIndex.get(scanId) : undefined;
		const at = i === undefined ? null : scans[i].started_at;
		return at ? formatMonthDay(at) : '';
	}
	function daysSince(iso: string | null | undefined): string {
		if (!iso) return '';
		const days = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000));
		return plural(days, 'day');
	}

	let firstSeen = $derived(row.first_seen_at ? formatDayOrDate(row.first_seen_at) : '');
	let firstSeenHint = $derived(
		row.first_seen_at
			? `${formatDateTime(row.first_seen_at)} · ${relativeTimeLong(row.first_seen_at)}`
			: null
	);
	let hosts = $derived.by(() => {
		const more = row.host_count - row.hosts.length;
		return [...row.hosts, ...(more > 0 ? [`${more} more`] : [])].join(' · ');
	});

	let lastChange = $derived.by(() => {
		if (!row.last_change_scan_id) return '';
		const i = scanIndex.get(row.last_change_scan_id);
		if (i === undefined) return '';
		const cell = row.cells[i];
		const parts: string[] = [];
		if (cell.opened.length) parts.push(`${cell.opened.map((c) => c.port).join(', ')} opened`);
		if (cell.closed.length) parts.push(`${cell.closed.map((c) => c.port).join(', ')} closed`);
		if (cell.software.length)
			parts.push(`software on ${cell.software.map((c) => c.port).join(', ')}`);
		return [dateOf(row.last_change_scan_id), ...parts].join(' · ');
	});

	function laneName(lane: ServiceLane): string {
		const software = [lane.product, lane.version].filter(Boolean).join(' ');
		return [lane.service_name, software].filter(Boolean).join(' · ');
	}
	function laneStatus(lane: ServiceLane): string {
		if (lane.open_now) {
			if (lane.opened_scan_id && lane.opened_scan_id !== scans[0]?.id) {
				const at = scans[scanIndex.get(lane.opened_scan_id) ?? 0]?.started_at;
				return `Opened ${dateOf(lane.opened_scan_id)} · ${daysSince(at)}`;
			}
			return lane.first_seen_at
				? `Open since ${formatDayOrDate(lane.first_seen_at)} · ${daysSince(lane.first_seen_at)}`
				: 'Open';
		}
		if (lane.closed_scan_id) {
			const since = lane.first_seen_at
				? `, was open since ${formatDayOrDate(lane.first_seen_at)}`
				: '';
			return `Closed ${dateOf(lane.closed_scan_id)}${since}`;
		}
		return 'Closed';
	}
	function chipClass(lane: ServiceLane): string {
		if (!lane.open_now)
			return 'border border-dashed border-border text-muted-foreground line-through';
		if (lane.opened_scan_id) return 'bg-foreground text-background';
		return 'bg-muted text-foreground';
	}
	function pickLane(lane: ServiceLane, i: number) {
		const cell = lane.cells[i];
		if (cell?.service_id) onOpenService(cell.service_id, scans[i].id);
	}
</script>

<div
	class="group flex cursor-pointer items-center gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-row-index={index}
	aria-expanded={expanded}
	aria-label="{expanded ? 'Collapse' : 'Expand'} {row.ip}"
	onclick={() => onToggle(row.ip)}
	onkeydown={(e) => {
		if (e.target !== e.currentTarget) return;
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onToggle(row.ip);
		}
	}}
>
	<div
		class="sticky left-0 z-[1] flex min-w-0 items-start gap-2 bg-card pr-2 {ADDRESS_LEAD_COLUMNS[0]
			.width}"
	>
		<ChevronRight
			class="mt-1 size-3.5 shrink-0 text-muted-foreground transition-transform {expanded
				? 'rotate-90'
				: ''}"
		/>
		<div class="min-w-0">
			<button
				type="button"
				class="rounded-sm font-mono text-sm leading-5 font-medium underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/70"
				onclick={(e) => {
					stopProp(e);
					onAddress(row.ip);
				}}
			>
				{row.ip}
			</button>
			{#if isNew}
				<span class="ml-1.5 rounded-sm border px-1 text-2xs text-muted-foreground">New</span>
			{/if}
			<div class="truncate text-xs text-muted-foreground">
				{hosts}{#if row.is_cdn}{hosts ? ' · ' : ''}CDN{/if}
			</div>
		</div>
	</div>

	{#each ADDRESS_COLUMNS as col (col.key)}
		<div class={columnCell(col)}>
			{#if col.key === 'strip'}
				<AddressStrip
					cells={row.cells}
					{scans}
					ip={row.ip}
					{highlight}
					{onHover}
					onPick={() => onToggle(row.ip)}
				/>
			{:else if col.key === 'open'}
				<span class="flex min-w-0 flex-wrap items-center gap-1 text-xs">
					{#each row.lanes.slice(0, MAX_CHIPS) as lane (`${lane.port}/${lane.protocol}`)}
						<span class="rounded-[4px] px-1.5 font-mono text-2xs {chipClass(lane)}"
							>{lane.port}</span
						>
					{/each}
					{#if row.lanes.length > MAX_CHIPS}
						<span class="text-2xs text-muted-foreground">+{row.lanes.length - MAX_CHIPS}</span>
					{/if}
					<span class="ml-1 text-muted-foreground">{row.open_now} open</span>
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
				<span class="text-xs tabular-nums {row.changes ? '' : 'text-muted-foreground'}">
					{row.changes.toLocaleString()}
				</span>
			{:else if col.key === 'last'}
				<span class="truncate text-xs text-muted-foreground">{lastChange || 'Unchanged'}</span>
			{/if}
		</div>
	{/each}
</div>

{#if expanded}
	<div class="bg-muted/20">
		{#each row.lanes as lane (`${lane.port}/${lane.protocol}`)}
			<div class="flex items-center gap-3 px-4 py-1.5">
				<div class="flex min-w-0 items-baseline gap-2 pl-6 {ADDRESS_LEAD_COLUMNS[0].width}">
					<span class="font-mono text-xs font-medium">{lane.port}/{lane.protocol}</span>
					<span class="truncate text-xs text-muted-foreground">{laneName(lane)}</span>
				</div>
				{#each ADDRESS_COLUMNS as col (col.key)}
					<div class={columnCell(col)}>
						{#if col.key === 'strip'}
							<LaneStrip
								cells={lane.cells}
								{scans}
								label="{lane.port}/{lane.protocol}"
								{highlight}
								{onHover}
								onPick={(i) => pickLane(lane, i)}
							/>
						{:else if col.key === 'open'}
							<span class="truncate text-xs text-muted-foreground">{laneStatus(lane)}</span>
						{:else if col.key === 'changes'}
							<span class="text-xs text-muted-foreground tabular-nums"
								>{lane.events + lane.software_changes || ''}</span
							>
						{:else if col.key === 'last' && lane.software_changes}
							<span class="truncate text-xs text-muted-foreground"
								>{plural(lane.software_changes, 'software change')}</span
							>
						{/if}
					</div>
				{/each}
			</div>
		{/each}
	</div>
{/if}
