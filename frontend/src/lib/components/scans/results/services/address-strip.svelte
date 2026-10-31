<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import {
		ADDRESS_CELL,
		ADDRESS_STATE_LABELS,
		AddressState,
		Observation,
		SERVICE_OBSERVATION_LABELS
	} from '$lib/config/timeline';
	import type { AddressCell, PortChange, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { CELL_PX, stripWidth } from '../web-assets/timeline-columns';

	interface Props {
		cells: AddressCell[];
		scans: TimelineScan[];
		ip: string;
		/** the column every strip highlights */
		highlight?: number;
		onHover?: (index: number) => void;
		onPick?: (index: number) => void;
	}

	let { cells, scans, ip, highlight = -1, onHover, onPick }: Props = $props();

	let hovered = $state(-1);
	let anchor = $state<HTMLElement | null>(null);
	let open = $state(false);

	let last = $derived(cells.length - 1);
	let changes = $derived(
		cells.filter((c) => c.opened.length || c.closed.length || c.software.length).length
	);
	let summary = $derived(
		`${ip}: ${plural(changes, 'scan')} with a port change across ${plural(cells.length, 'scan')}`
	);

	const SILENT = new Set<string>([AddressState.UNCONFIRMED, AddressState.UNOBSERVED]);

	function when(i: number): string {
		const at = scans[i]?.started_at;
		return at ? formatDateTime(at) : '';
	}

	function headline(i: number): string {
		const cell = cells[i];
		const scan = scans[i];
		if (!cell || !scan) return '';
		const parts: string[] = [];
		if (cell.opened.length) parts.push(`${plural(cell.opened.length, 'port')} opened`);
		if (cell.closed.length) parts.push(`${plural(cell.closed.length, 'port')} closed`);
		if (cell.software.length) parts.push(`software changed on ${cell.software.length}`);
		if (!parts.length) parts.push(ADDRESS_STATE_LABELS[cell.state]);
		if (SILENT.has(cell.state) && scan.observation !== Observation.OBSERVED) {
			parts.push(SERVICE_OBSERVATION_LABELS[scan.observation]);
		}
		if (i === last) parts.push('This scan');
		return parts.join(' · ');
	}

	function service(c: PortChange): string {
		const software = [c.product, c.version].filter(Boolean).join(' ');
		return [c.service_name, software].filter(Boolean).join(' · ');
	}

	function why(c: PortChange, kind: 'opened' | 'closed'): string {
		if (kind === 'closed') {
			if (!c.open_since) return '';
			const days = Math.max(
				0,
				Math.round((Date.now() - new Date(c.open_since).getTime()) / 86_400_000)
			);
			return days
				? `open since ${formatMonthDay(c.open_since)}, ${plural(days, 'day')}`
				: `open since ${formatMonthDay(c.open_since)}`;
		}
		if (c.first_on_target) return 'first time on this target';
		if (c.first_on_address) return 'first time on this address';
		return 'open before';
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

	function ring(i: number, state: AddressState): string {
		if (hovered === i) return 'outline outline-offset-1 outline-foreground';
		if (highlight === i && state !== AddressState.UNSEEN)
			return 'outline outline-offset-1 outline-foreground/40';
		if (i === last)
			return state === AddressState.UNSEEN
				? 'outline outline-offset-1 outline-border'
				: 'outline outline-offset-1 outline-foreground/70';
		return '';
	}

	let shown = $derived(hovered >= 0 ? cells[hovered] : null);
</script>

{#snippet line(sign: string, c: PortChange, kind: 'opened' | 'closed' | 'software')}
	<div class="flex items-baseline gap-2 border-t border-border/60 py-1 first:border-t-0">
		<span class="w-3 font-mono font-semibold">{sign}</span>
		<span class="font-mono">{c.port}/{c.protocol}</span>
		<span class="min-w-0 truncate">{service(c)}</span>
		{#if kind !== 'software'}
			<span class="ml-auto whitespace-nowrap text-muted-foreground">{why(c, kind)}</span>
		{/if}
	</div>
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
						class="relative h-4 shrink-0 rounded-[2px] transition-[outline-color] {ADDRESS_CELL[
							cell.state
						]} {ring(i, cell.state)}"
						style="width: {CELL_PX}px"
					>
						{#if cell.software.length && !cell.opened.length && !cell.closed.length}
							<span
								class="absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground ring-1 ring-card"
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
			class="w-[26rem] rounded-lg border bg-popover p-3 text-popover-foreground shadow-md"
			arrowClasses="hidden"
		>
			<div class="flex flex-col gap-2">
				<div class="flex items-baseline justify-between gap-4">
					<span class="font-medium">{when(hovered)}</span>
					<span class="text-muted-foreground">{headline(hovered)}</span>
				</div>
				{#if shown.opened.length || shown.closed.length || shown.software.length}
					<div class="flex flex-col">
						{#each shown.opened as c (`${c.port}/${c.protocol}`)}
							{@render line('+', c, 'opened')}
						{/each}
						{#each shown.closed as c (`${c.port}/${c.protocol}`)}
							{@render line('−', c, 'closed')}
						{/each}
						{#each shown.software as c (`${c.port}/${c.protocol}`)}
							{@render line('~', c, 'software')}
						{/each}
					</div>
				{/if}
			</div>
		</Tooltip.Content>
	{/if}
</Tooltip.Root>
