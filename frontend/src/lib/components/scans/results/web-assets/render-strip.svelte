<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import {
		CAPTURED_STATES,
		Observation,
		RENDER_CELL,
		RENDER_OBSERVATION_LABELS,
		RENDER_STATE_LABELS,
		RenderState
	} from '$lib/config/timeline';
	import type { RenderCell, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { screenshotUrl } from '$lib/utilities/media';
	import { plural } from '$lib/utilities/strings';
	import { CELL_PX, stripWidth } from './timeline-columns';

	interface Props {
		cells: RenderCell[];
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
	let captured = $derived(cells.filter((c) => CAPTURED_STATES.has(c.state)));
	let summary = $derived(
		`${name}: ${plural(captured.length, 'capture')} across ${plural(cells.length, 'scan')}`
	);

	const SILENT = new Set<string>([RenderState.UNCONFIRMED, RenderState.UNOBSERVED]);

	function when(i: number): string {
		const at = scans[i]?.started_at;
		return at ? formatDateTime(at) : '';
	}

	function verdict(i: number): string {
		const cell = cells[i];
		const scan = scans[i];
		if (!cell || !scan) return '';
		const parts = [RENDER_STATE_LABELS[cell.state]];
		const previous = before(i);
		if (cell.state === RenderState.CHANGED && previous >= 0) {
			parts[0] = `Changed since ${formatMonthDay(scans[previous].started_at ?? '')}`;
		} else if (cell.state === RenderState.SAME && previous >= 0) {
			parts[0] = `Same as ${formatMonthDay(scans[previous].started_at ?? '')}`;
		}
		if (SILENT.has(cell.state) && scan.observation !== Observation.OBSERVED) {
			parts.push(RENDER_OBSERVATION_LABELS[scan.observation]);
		}
		if (i === last) parts.push('This scan');
		return parts.join(' · ');
	}

	// the capture this cell was compared with
	function before(i: number): number {
		for (let j = i - 1; j >= 0; j -= 1) if (CAPTURED_STATES.has(cells[j].state)) return j;
		return -1;
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

	function ring(i: number, state: RenderState): string {
		if (hovered === i) return 'outline outline-offset-1 outline-foreground';
		if (highlight === i && state !== RenderState.UNSEEN)
			return 'outline outline-offset-1 outline-foreground/40';
		if (i === last)
			return state === RenderState.UNSEEN
				? 'outline outline-offset-1 outline-border'
				: 'outline outline-offset-1 outline-foreground/70';
		return '';
	}

	let shown = $derived(hovered >= 0 ? cells[hovered] : null);
	let shownCaptured = $derived(!!shown && CAPTURED_STATES.has(shown.state));
	let compared = $derived(
		shown?.state === RenderState.CHANGED && hovered >= 0 ? before(hovered) : -1
	);
</script>

{#snippet frame(i: number, caption: string)}
	{@const url = screenshotUrl(cells[i]?.path)}
	<figure class="m-0 flex w-56 flex-col gap-1">
		<div class="aspect-[16/10] w-full overflow-hidden rounded-md border bg-muted">
			{#if url}
				<img
					src={url}
					alt="Screenshot of {name}, {when(i)}"
					decoding="async"
					class="h-full w-full object-cover object-top"
				/>
			{:else}
				<div class="flex h-full w-full items-center justify-center text-muted-foreground">
					Image removed
				</div>
			{/if}
		</div>
		<figcaption class="flex justify-between gap-2 text-2xs text-muted-foreground">
			<span>{formatMonthDay(scans[i]?.started_at ?? '')}</span>
			<span>{caption}</span>
		</figcaption>
	</figure>
{/snippet}

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
						class="relative h-4 shrink-0 rounded-[2px] transition-[outline-color] {RENDER_CELL[
							cell.state
						]} {ring(i, cell.state)}"
						style="width: {CELL_PX}px"
					>
						{#if CAPTURED_STATES.has(cell.state) && !cell.path}
							<span
								class="absolute inset-x-0 bottom-0 h-1 bg-[repeating-linear-gradient(135deg,var(--fill-hatch)_0_2px,transparent_2px_4px)]"
							></span>
						{/if}
					</span>
				{/each}
			</div>
		{/snippet}
	</Tooltip.Trigger>
	{#if hovered >= 0 && shown}
		<Tooltip.Content
			customAnchor={anchor}
			side="top"
			sideOffset={8}
			class="rounded-lg border bg-popover p-3 text-popover-foreground shadow-md"
			arrowClasses="hidden"
		>
			<div class="flex flex-col gap-2">
				<div class="flex items-baseline justify-between gap-4">
					<span class="font-medium">{when(hovered)}</span>
					<span class="text-muted-foreground">{verdict(hovered)}</span>
				</div>
				{#if shownCaptured && compared >= 0}
					<div class="flex gap-3">
						{@render frame(compared, 'Before')}
						{@render frame(hovered, 'After')}
					</div>
				{:else if shownCaptured}
					{@render frame(hovered, '')}
				{/if}
			</div>
		</Tooltip.Content>
	{/if}
</Tooltip.Root>
