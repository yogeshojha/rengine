<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import {
		LANE_CELL,
		LANE_STATE_LABELS,
		LaneState,
		Observation,
		SERVICE_OBSERVATION_LABELS
	} from '$lib/config/timeline';
	import type { LaneCell, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { CELL_PX, stripWidth } from '../web-assets/timeline-columns';

	interface Props {
		cells: LaneCell[];
		scans: TimelineScan[];
		label: string;
		highlight?: number;
		onHover?: (index: number) => void;
		onPick?: (index: number) => void;
	}

	let { cells, scans, label, highlight = -1, onHover, onPick }: Props = $props();

	let hovered = $state(-1);
	let anchor = $state<HTMLElement | null>(null);
	let open = $state(false);

	let last = $derived(cells.length - 1);
	let openCount = $derived(cells.filter((c) => c.state === LaneState.OPEN).length);
	let summary = $derived(
		`${label}: open in ${plural(openCount, 'scan')} of ${plural(cells.length, 'scan')}`
	);

	const SILENT = new Set<string>([LaneState.UNCONFIRMED, LaneState.UNOBSERVED]);

	function tip(i: number): string {
		const cell = cells[i];
		const scan = scans[i];
		if (!cell || !scan) return '';
		const when = scan.started_at ? formatDateTime(scan.started_at) : '';
		const parts = [when, LANE_STATE_LABELS[cell.state]];
		if (cell.software_changed) parts.push('Software changed');
		if (SILENT.has(cell.state) && scan.observation !== Observation.OBSERVED) {
			parts.push(SERVICE_OBSERVATION_LABELS[scan.observation]);
		}
		if (i === last) parts.push('This scan');
		return parts.filter(Boolean).join(' · ');
	}

	function cellOf(e: Event): HTMLElement | null {
		return e.target instanceof Element ? e.target.closest<HTMLElement>('[data-cell]') : null;
	}
	function track(e: MouseEvent) {
		const el = cellOf(e);
		if (!el) return;
		const i = Number(el.dataset.cell);
		if (i !== hovered) {
			hovered = i;
			anchor = el;
			onHover?.(i);
		}
		open = true;
	}
	function leave() {
		open = false;
		hovered = -1;
		onHover?.(-1);
	}
	function pick(e: MouseEvent) {
		const el = cellOf(e);
		if (!el || !onPick) return;
		e.stopPropagation();
		onPick(Number(el.dataset.cell));
	}

	function ring(i: number, state: LaneState): string {
		if (hovered === i) return 'outline outline-offset-1 outline-foreground';
		if (highlight === i && state !== LaneState.UNSEEN)
			return 'outline outline-offset-1 outline-foreground/40';
		if (i === last)
			return state === LaneState.UNSEEN
				? 'outline outline-offset-1 outline-border'
				: 'outline outline-offset-1 outline-foreground/70';
		return '';
	}
</script>

<Tooltip.Root bind:open disableHoverableContent>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				{...props}
				role="img"
				aria-label={summary}
				class="flex h-4 items-center gap-0.5"
				style="width: {stripWidth(cells.length)}px"
				onmousemove={track}
				onmouseleave={leave}
				onclick={pick}
			>
				{#each cells as cell, i (i)}
					<span
						data-cell={i}
						class="relative h-3 shrink-0 rounded-[2px] transition-[outline-color] {LANE_CELL[
							cell.state
						]} {ring(i, cell.state)}"
						style="width: {CELL_PX}px"
					>
						{#if cell.software_changed}
							<span
								class="absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-background ring-1 ring-foreground/60"
							></span>
						{/if}
					</span>
				{/each}
			</div>
		{/snippet}
	</Tooltip.Trigger>
	{#if hovered >= 0}
		<Tooltip.Content customAnchor={anchor} side="top" sideOffset={6}>
			{tip(hovered)}
		</Tooltip.Content>
	{/if}
</Tooltip.Root>
