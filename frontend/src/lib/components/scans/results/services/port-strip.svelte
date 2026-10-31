<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { AddressState, Observation, SERVICE_OBSERVATION_LABELS } from '$lib/config/timeline';
	import type { PortCell, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { stripWidth } from '../web-assets/timeline-columns';
	import { MATRIX_CELL_PX } from './timeline-columns';

	interface Props {
		cells: PortCell[];
		scans: TimelineScan[];
		label: string;
		peak: number;
		highlight?: number;
		onHover?: (index: number) => void;
		onPick?: (index: number) => void;
	}

	let { cells, scans, label, peak, highlight = -1, onHover, onPick }: Props = $props();

	let hovered = $state(-1);
	let anchor = $state<HTMLElement | null>(null);
	let open = $state(false);

	let last = $derived(cells.length - 1);
	let summary = $derived(
		`${label}: up to ${plural(peak, 'address')} across ${plural(cells.length, 'scan')}`
	);

	const HATCH =
		'bg-[repeating-linear-gradient(135deg,var(--fill-hatch)_0_2px,transparent_2px_5px)]';

	// the fill darkens with the share of the peak
	function fill(cell: PortCell): string {
		if (cell.state === AddressState.UNOBSERVED) return HATCH;
		if (cell.state === AddressState.UNCONFIRMED)
			return `border border-dashed border-fill-hatch ${HATCH}`;
		if (cell.count === 0) return 'border border-border/70 text-muted-foreground';
		const share = peak > 0 ? cell.count / peak : 1;
		if (share > 0.75) return 'bg-fill-strong text-background';
		if (share > 0.4) return 'bg-fill-muted';
		return 'bg-fill-muted/50';
	}

	function ring(i: number, cell: PortCell): string {
		if (hovered === i) return 'outline outline-offset-1 outline-foreground';
		if (cell.delta > 0) return 'outline-2 outline-offset-[-2px] outline-foreground outline';
		if (cell.delta < 0) return 'outline-2 outline-offset-[-2px] outline-foreground outline-dashed';
		if (highlight === i) return 'outline outline-offset-1 outline-foreground/40';
		if (i === last) return 'outline outline-offset-1 outline-foreground/70';
		return '';
	}

	function when(i: number): string {
		const at = scans[i]?.started_at;
		return at ? formatDateTime(at) : '';
	}

	function headline(i: number): string {
		const cell = cells[i];
		const scan = scans[i];
		if (!cell || !scan) return '';
		if (cell.state === AddressState.UNOBSERVED) return SERVICE_OBSERVATION_LABELS[scan.observation];
		const parts = [`on ${plural(cell.count, 'address')}`];
		if (cell.delta > 0) parts.push(`${cell.delta} more than the run before`);
		if (cell.delta < 0) parts.push(`${-cell.delta} fewer than the run before`);
		if (cell.state === AddressState.UNCONFIRMED && scan.observation !== Observation.OBSERVED) {
			parts.push(SERVICE_OBSERVATION_LABELS[scan.observation]);
		}
		if (i === last) parts.push('This scan');
		return parts.join(' · ');
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

	let shown = $derived(hovered >= 0 ? cells[hovered] : null);
</script>

<Tooltip.Root bind:open disableHoverableContent>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				{...props}
				role="img"
				aria-label={summary}
				class="flex h-6 items-center gap-0.5"
				style="width: {stripWidth(cells.length, MATRIX_CELL_PX)}px"
				onmousemove={track}
				onmouseleave={leave}
				onclick={pick}
			>
				{#each cells as cell, i (i)}
					<span
						data-cell={i}
						class="flex h-5 shrink-0 items-center justify-center rounded-[3px] font-mono text-2xs tabular-nums transition-[outline-color] {fill(
							cell
						)} {ring(i, cell)}"
						style="width: {MATRIX_CELL_PX}px"
					>
						{#if cell.state !== AddressState.UNOBSERVED && cell.count > 0 && cell.count < 100}
							{cell.count}
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
			class="w-[22rem] rounded-lg border bg-popover p-3 text-popover-foreground shadow-md"
			arrowClasses="hidden"
		>
			<div class="flex flex-col gap-2">
				<div class="flex items-baseline justify-between gap-4">
					<span class="font-medium">{when(hovered)}</span>
					<span class="text-muted-foreground">{headline(hovered)}</span>
				</div>
				{#if shown.added.length || shown.removed.length}
					<div class="flex flex-col">
						{#each shown.added as ip (ip)}
							<div
								class="flex items-baseline gap-2 border-t border-border/60 py-1 first:border-t-0"
							>
								<span class="w-3 font-mono font-semibold">+</span>
								<span class="font-mono">{ip}</span>
							</div>
						{/each}
						{#each shown.removed as ip (ip)}
							<div
								class="flex items-baseline gap-2 border-t border-border/60 py-1 first:border-t-0"
							>
								<span class="w-3 font-mono font-semibold">−</span>
								<span class="font-mono">{ip}</span>
							</div>
						{/each}
						{#if shown.more}
							<div class="border-t border-border/60 py-1 text-muted-foreground">
								and {plural(shown.more, 'more address')}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</Tooltip.Content>
	{/if}
</Tooltip.Root>
