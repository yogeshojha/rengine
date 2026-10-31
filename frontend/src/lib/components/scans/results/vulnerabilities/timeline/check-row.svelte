<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Hint from '$lib/components/hint.svelte';
	import {
		CHECK_CELL,
		CHECK_STATE_LABELS,
		CheckFlag,
		CheckState,
		FINDING_OBSERVATION_LABELS,
		Observation
	} from '$lib/config/timeline';
	import { SEVERITY_CHIP, SEVERITY_FILL, severityLabel } from '$lib/config/vulnerabilities';
	import type { CheckCell, CheckRow, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { pinnedTone, rowTone } from '../../table/columns';
	import { CELL_GAP_PX, stripWidth } from '../../web-assets/timeline-columns';
	import { MATRIX_CELL_PX } from '../../services/timeline-columns';
	import { CHECK_PX, HOSTS_PX } from './columns';

	interface Props {
		row: CheckRow;
		scans: TimelineScan[];
		index: number;
		focused: boolean;
		pad: string;
		highlight: number;
		onHover: (index: number) => void;
		onOpen: (templateId: string) => void;
		onOpenScan: (scanId: string) => void;
	}

	let { row, scans, index, focused, pad, highlight, onHover, onOpen, onOpenScan }: Props = $props();

	let n = $derived(scans.length);
	let last = $derived(n - 1);
	let width = $derived(stripWidth(n, MATRIX_CELL_PX));
	let fill = $derived(SEVERITY_FILL[row.severity] ?? SEVERITY_FILL.unknown);
	let chip = $derived(SEVERITY_CHIP[row.severity] ?? SEVERITY_CHIP.unknown);
	let hovered = $state(-1);
	let open = $state(false);
	let anchor = $state<HTMLElement | null>(null);

	function dateOf(id: string | null): string {
		const at = id ? scans.find((s) => s.id === id)?.started_at : null;
		return at ? formatMonthDay(at) : '';
	}
	let lastCell = $derived(row.cells[last]);
	let hostsNow = $derived(
		row.hosts_now == null
			? CHECK_STATE_LABELS[lastCell?.state ?? CheckState.NOT_TESTED]
			: row.hosts_now === row.peak || !row.peak
				? plural(row.hosts_now, 'web asset')
				: `${row.hosts_now} of ${plural(row.peak, 'web asset')}`
	);
	let note = $derived.by(() => {
		if (row.flags.includes(CheckFlag.CLEARED)) return `cleared ${dateOf(row.last_change_scan_id)}`;
		if (row.flags.includes(CheckFlag.LIBRARY_NEW))
			return `first tested ${dateOf(row.library_scan_id)}`;
		if (row.flags.includes(CheckFlag.SHRANK))
			return `shrank · last change ${dateOf(row.last_change_scan_id)}`;
		if (row.flags.includes(CheckFlag.SPREAD))
			return `spread · last change ${dateOf(row.last_change_scan_id)}`;
		return row.first_seen_at ? `since ${formatMonthDay(row.first_seen_at)}` : '';
	});

	function shade(cell: CheckCell): string {
		if (!cell.hosts || !row.peak) return '';
		const share = cell.hosts / row.peak;
		return `background: color-mix(in oklch, ${fill} ${share > 0.66 ? 100 : share > 0.33 ? 70 : 45}%, var(--card))`;
	}
	function edge(cell: CheckCell): string {
		if (cell.delta > 0) return 'outline-2 outline-offset-[-2px] outline-foreground outline';
		if (cell.delta < 0) return 'outline-2 outline-offset-[-2px] outline-foreground outline-dashed';
		return '';
	}
	function ring(i: number): string {
		if (hovered === i) return 'ring-1 ring-foreground ring-offset-1 ring-offset-card';
		if (highlight === i) return 'ring-1 ring-foreground/40 ring-offset-1 ring-offset-card';
		if (i === last) return 'ring-1 ring-foreground/70 ring-offset-1 ring-offset-card';
		return '';
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
			onHover(i);
		}
		open = true;
	}
	function leave() {
		open = false;
		hovered = -1;
		onHover(-1);
	}
	function pick(e: MouseEvent) {
		const el = cellOf(e);
		if (!el) return;
		const i = Number(el.dataset.cell);
		if (i !== last && scans[i]) onOpenScan(scans[i].id);
	}
	let shown = $derived(hovered >= 0 ? row.cells[hovered] : null);
	let headline = $derived.by(() => {
		if (!shown) return '';
		const scan = scans[hovered];
		if (shown.state !== CheckState.TESTED) {
			const parts = [CHECK_STATE_LABELS[shown.state]];
			if (shown.state === CheckState.NOT_TESTED && scan?.observation === Observation.PARTIAL)
				parts.push(FINDING_OBSERVATION_LABELS[scan.observation]);
			return parts.join(' · ');
		}
		const parts = [plural(shown.hosts, 'web asset')];
		if (shown.delta)
			parts.push(`${shown.delta > 0 ? '+' : '−'}${Math.abs(shown.delta)} since the run before`);
		if (hovered === last) parts.push('This scan');
		return parts.join(' · ');
	});
	let summary = $derived(
		`${row.template_name}: ${hostsNow} now, ${plural(row.peak, 'web asset')} at most across ${plural(n, 'run')}`
	);
</script>

<div
	role="row"
	tabindex="-1"
	data-vuln-row-index={index}
	class="group flex items-center gap-6 pr-4 pl-4 outline-none {rowTone(false, focused)} {pad}"
>
	<div
		class="sticky left-0 z-[1] min-w-0 shrink-0 pr-2 {pinnedTone(focused)}"
		style="width: {CHECK_PX}px"
	>
		<button
			type="button"
			class="block max-w-full truncate text-left text-sm font-semibold outline-none hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/70"
			onclick={() => onOpen(row.template_id)}
		>
			{row.template_name}
		</button>
		<div class="mt-1 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
			<code class="truncate font-mono text-2xs">{row.template_id}</code>
			<span class="shrink-0 rounded px-1 text-2xs font-semibold {chip.chip}">
				{severityLabel(row.severity)}
			</span>
			{#if row.is_kev}
				<Hint text="Listed in CISA KEV">
					{#snippet child(props)}
						<span
							{...props}
							class="inline-flex shrink-0 items-center gap-0.5 rounded bg-destructive/10 px-1 text-2xs font-semibold text-destructive"
						>
							<Flame class="size-2.5" /> KEV
						</span>
					{/snippet}
				</Hint>
			{/if}
		</div>
	</div>

	<Tooltip.Root bind:open disableHoverableContent>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
				<div
					{...props}
					role="img"
					aria-label={summary}
					class="flex shrink-0 items-center"
					style="width: {width}px; gap: {CELL_GAP_PX}px"
					onmousemove={track}
					onmouseleave={leave}
					onclick={pick}
				>
					{#each row.cells as cell, i (i)}
						<span
							data-cell={i}
							class="flex shrink-0 items-center justify-center rounded-[3px] text-2xs font-medium tabular-nums {cell.hosts
								? ''
								: CHECK_CELL[cell.state]} {edge(cell)} {ring(i)}"
							style="width: {MATRIX_CELL_PX}px; height: {MATRIX_CELL_PX}px; {shade(cell)}"
						>
							{#if cell.hosts && cell.hosts < 100}
								<span class="text-foreground mix-blend-luminosity">{cell.hosts}</span>
							{/if}
						</span>
					{/each}
				</div>
			{/snippet}
		</Tooltip.Trigger>
		{#if shown && anchor && hovered >= 0}
			<Tooltip.Content
				customAnchor={anchor}
				side="top"
				sideOffset={8}
				class="w-80 rounded-lg border bg-popover p-3 text-xs text-popover-foreground shadow-md"
				arrowClasses="hidden"
			>
				<div class="flex flex-col gap-1.5">
					<div class="flex items-baseline justify-between gap-3">
						<span class="font-medium">
							{formatDateTime(scans[hovered]?.started_at ?? '')}
						</span>
						<span class="text-muted-foreground">{headline}</span>
					</div>
					{#if shown.added.length || shown.removed.length}
						<div class="flex flex-col">
							{#each shown.added as host (host)}
								<div
									class="flex items-baseline gap-2 border-t border-border/60 py-1 first:border-t-0"
								>
									<span class="w-3 font-mono font-semibold">+</span>
									<span class="min-w-0 truncate font-mono">{host}</span>
								</div>
							{/each}
							{#each shown.removed as host (host)}
								<div
									class="flex items-baseline gap-2 border-t border-border/60 py-1 first:border-t-0"
								>
									<span class="w-3 font-mono font-semibold">−</span>
									<span class="min-w-0 truncate font-mono">{host}</span>
								</div>
							{/each}
							{#if shown.more}
								<div class="border-t border-border/60 py-1 text-muted-foreground">
									and {shown.more} more
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</Tooltip.Content>
		{/if}
	</Tooltip.Root>

	<div class="ml-auto shrink-0 text-right" style="width: {HOSTS_PX}px">
		<span class="text-sm font-semibold tabular-nums">{hostsNow}</span>
		{#if note}<div class="mt-0.5 truncate text-2xs text-muted-foreground">{note}</div>{/if}
	</div>
</div>
