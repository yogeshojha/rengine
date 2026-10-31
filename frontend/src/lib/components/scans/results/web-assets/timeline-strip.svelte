<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import {
		OBSERVATION_LABELS,
		Observation,
		SILENT_STATES,
		STATE_CELL,
		WEB_STATE_LABELS,
		WebAssetState
	} from '$lib/config/timeline';
	import type { TimelineCell, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { CELL_PX, stripWidth } from './timeline-columns';

	interface Props {
		cells: TimelineCell[];
		scans: TimelineScan[];
		name: string;
		/** the column every strip highlights */
		highlight?: number;
		onHover?: (index: number) => void;
		onPick?: (index: number) => void;
	}

	let { cells, scans, name, highlight = -1, onHover, onPick }: Props = $props();

	let hovered = $state(-1);
	let anchor = $state<HTMLElement | null>(null);
	let open = $state(false);

	let last = $derived(cells.length - 1);
	let present = $derived(
		cells.filter((c) => !SILENT_STATES.has(c.state) && c.state !== WebAssetState.UNSEEN)
	);
	let summary = $derived(
		`${name}: ${plural(present.length, 'scan')} with a row across ${plural(cells.length, 'scan')}`
	);

	function tip(i: number): string {
		const cell = cells[i];
		const scan = scans[i];
		if (!cell || !scan) return '';
		const when = scan.started_at ? formatDateTime(scan.started_at) : '';
		const state =
			cell.status != null
				? `${cell.status} ${WEB_STATE_LABELS[cell.state]}`
				: WEB_STATE_LABELS[cell.state];
		const parts = [when, state];
		if (SILENT_STATES.has(cell.state) && scan.observation !== Observation.OBSERVED) {
			parts.push(OBSERVATION_LABELS[scan.observation]);
		}
		if (cell.changed.length) parts.push(`${cell.changed.join(', ')} changed`);
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

	function ring(i: number, state: WebAssetState): string {
		if (hovered === i) return 'outline outline-offset-1 outline-foreground';
		if (highlight === i && state !== WebAssetState.UNSEEN)
			return 'outline outline-offset-1 outline-foreground/40';
		if (i === last)
			return state === WebAssetState.UNSEEN
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
				class="flex h-5 items-center gap-0.5"
				style="width: {stripWidth(cells.length)}px"
				onmousemove={track}
				onmouseleave={leave}
				onclick={pick}
			>
				{#each cells as cell, i (i)}
					<span
						data-cell={i}
						class="relative h-4 shrink-0 rounded-[2px] transition-[outline-color] {STATE_CELL[
							cell.state
						]} {ring(i, cell.state)}"
						style="width: {CELL_PX}px"
					>
						{#if cell.changed.length}
							<span
								class="absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground ring-1 ring-card"
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
