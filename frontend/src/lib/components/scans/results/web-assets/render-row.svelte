<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import ScreenshotThumb from '../screenshot-thumb.svelte';
	import RenderStrip from './render-strip.svelte';
	import {
		CAPTURED_STATES,
		RENDER_STATE_LABELS,
		RenderFlag,
		RenderState
	} from '$lib/config/timeline';
	import type { RenderRow, TimelineScan } from '$lib/types/timeline';
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
	import { RENDER_COLUMNS, RENDER_LEAD_COLUMNS } from './timeline-columns';

	interface Props {
		row: RenderRow;
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
	let isNew = $derived(row.flags.includes(RenderFlag.NEW));
	let scanIndex = $derived(new Map(scans.map((s, i) => [s.id, i])));

	function dateOf(scanId: string | null): string {
		const i = scanId ? scanIndex.get(scanId) : undefined;
		const at = i === undefined ? null : scans[i].started_at;
		return at ? formatMonthDay(at) : '';
	}

	let firstCaptured = $derived(row.first_capture_at ? formatDayOrDate(row.first_capture_at) : '');
	let firstCapturedHint = $derived(
		row.first_capture_at
			? `${formatDateTime(row.first_capture_at)} · ${relativeTimeLong(row.first_capture_at)}`
			: null
	);

	// the newest cell that is not silence about the host
	let now = $derived.by(() => {
		for (let i = row.cells.length - 1; i >= 0; i -= 1) {
			const cell = row.cells[i];
			if (cell.state !== RenderState.UNCONFIRMED && cell.state !== RenderState.UNOBSERVED) {
				return cell;
			}
		}
		return null;
	});
	let nowCaptured = $derived(!!now && CAPTURED_STATES.has(now.state));

	let lastChange = $derived.by(() => {
		if (!row.last_change_scan_id) return '';
		const i = scanIndex.get(row.last_change_scan_id);
		if (i === undefined) return '';
		const cell = row.cells[i];
		const date = dateOf(row.last_change_scan_id);
		if (cell.state === RenderState.FIRST) return `${date} · First screenshot`;
		return `${date} · Changed`;
	});

	function pick(i: number) {
		const state = row.cells[i]?.state;
		const hasRow =
			!!state &&
			state !== RenderState.UNSEEN &&
			state !== RenderState.GONE &&
			state !== RenderState.UNCONFIRMED &&
			state !== RenderState.UNOBSERVED;
		if (hasRow) onOpenAt(host, scans[i].id);
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
	<div class="flex min-w-0 items-center {RENDER_LEAD_COLUMNS[0].width}">
		<span class="min-w-0 font-mono text-sm leading-5 font-medium wrap-anywhere">
			{#each headLabels as part, i (i)}{part}{#if i < headLabels.length - 1}.<wbr
					/>{/if}{/each}{#if apexSuffix}<wbr /><span class="font-normal text-muted-foreground"
					>{apexSuffix}</span
				>{/if}
		</span>
	</div>

	{#each RENDER_COLUMNS as col (col.key)}
		<div class={columnCell(col)}>
			{#if col.key === 'strip'}
				<RenderStrip
					cells={row.cells}
					{scans}
					name={host.name}
					{highlight}
					{onHover}
					onPick={pick}
				/>
			{:else if col.key === 'now'}
				<span class="flex min-w-0 items-center gap-2">
					{#if nowCaptured && now?.path}
						<ScreenshotThumb path={now.path} alt={host.name} class="h-9 w-16" preview />
					{:else if now}
						<span class="truncate text-xs text-muted-foreground"
							>{nowCaptured ? 'Image removed' : RENDER_STATE_LABELS[now.state]}</span
						>
					{/if}
					{#if isNew}
						<Badge variant="outline" class="px-1.5 text-2xs">New</Badge>
					{/if}
				</span>
			{:else if col.key === 'first'}
				<Hint text={firstCapturedHint}>
					{#snippet child(props)}
						<span {...props} class="truncate text-xs text-muted-foreground tabular-nums"
							>{firstCaptured}</span
						>
					{/snippet}
				</Hint>
			{:else if col.key === 'changes'}
				<span class="text-xs tabular-nums {row.changes ? '' : 'text-muted-foreground'}">
					{row.changes.toLocaleString()}
				</span>
			{:else if col.key === 'last'}
				{#if lastChange}
					<button
						type="button"
						class="truncate rounded-sm text-left text-xs text-muted-foreground underline-offset-2 outline-none hover:text-foreground hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/70"
						aria-label="Open {host.name} as recorded when its screenshot last changed"
						onclick={openLastChange}
					>
						{lastChange}
					</button>
				{:else}
					<span class="truncate text-xs text-muted-foreground">No screenshots</span>
				{/if}
			{/if}
		</div>
	{/each}
</div>
