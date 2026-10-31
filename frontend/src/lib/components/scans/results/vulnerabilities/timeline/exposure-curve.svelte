<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { FINDING_OBSERVATION_LABELS, HATCH, Observation } from '$lib/config/timeline';
	import { SEVERITY_FILL, SEVERITY_ORDER, severityLabel } from '$lib/config/vulnerabilities';
	import type { RunPoint, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { axisLabels, columnAt, shiftClass } from './geometry';

	interface Props {
		runs: RunPoint[];
		scans: TimelineScan[];
		highlight: number;
		onHover: (index: number) => void;
		onOpenScan: (scanId: string) => void;
	}

	let { runs, scans, highlight, onHover, onOpenScan }: Props = $props();

	const PLOT_PX = 48;
	const GAP_PX = 3;
	const UNOBSERVED_PX = 30;

	let n = $derived(runs.length);
	let last = $derived(n - 1);
	let px = $derived(n > 30 ? 8 : 12);
	let step = $derived(px + GAP_PX);
	let width = $derived(Math.max(0, n * step - GAP_PX));
	let peak = $derived(
		Math.max(1, ...runs.map((r) => Object.values(r.open).reduce((a, b) => a + b, 0)))
	);
	let stack = $derived([...SEVERITY_ORDER].reverse());
	let labels = $derived(axisLabels(scans, width + GAP_PX));

	let hovered = $state(-1);
	let open = $state(false);
	let dragging = $state(false);
	let anchor = $state<HTMLElement | null>(null);

	function height(count: number): number {
		return count ? Math.max(2, Math.round((count / peak) * PLOT_PX)) : 0;
	}
	function observed(i: number): boolean {
		return scans[i]?.observation !== Observation.UNOBSERVED;
	}
	function total(point: RunPoint): number {
		return Object.values(point.open).reduce((a, b) => a + b, 0);
	}
	function breakdown(point: RunPoint): string {
		return SEVERITY_ORDER.filter((s) => point.open[s])
			.map((s) => `${point.open[s]} ${severityLabel(s).toLowerCase()}`)
			.join(', ');
	}
	function tested(point: RunPoint): string {
		const parts: string[] = [];
		if (point.tested_checks != null) parts.push(plural(point.tested_checks, 'check'));
		if (point.tested_origins != null) parts.push(plural(point.tested_origins, 'origin'));
		return parts.join(' · ');
	}
	function at(e: PointerEvent | MouseEvent): number {
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		return columnAt(e.clientX - rect.left, n, width + GAP_PX);
	}
	function move(e: PointerEvent) {
		const i = at(e);
		if (i !== hovered) {
			hovered = i;
			onHover(i);
		}
		open = true;
	}
	function leave() {
		if (dragging) return;
		open = false;
		hovered = -1;
		onHover(-1);
	}
	function down(e: PointerEvent) {
		dragging = true;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		move(e);
	}
	function up(e: PointerEvent) {
		if (!dragging) return;
		dragging = false;
		const i = at(e);
		if (i >= 0 && i !== last && scans[i]) onOpenScan(scans[i].id);
	}
	function ring(i: number): string {
		if (i === last) return 'outline-2 outline-offset-2 outline-primary outline';
		if (i === highlight || i === hovered)
			return 'outline-2 outline-offset-2 outline-foreground/40 outline';
		return '';
	}
	let shown = $derived(hovered >= 0 ? runs[hovered] : null);
	let summary = $derived(`Open findings per run, ${plural(n, 'run')}, up to ${peak} open`);
</script>

<div class="flex min-w-0 flex-col gap-1.5">
	<div class="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
		Open findings per run
	</div>
	<Tooltip.Root bind:open disableHoverableContent>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<div
					{...props}
					role="img"
					aria-label={summary}
					class="relative flex touch-none items-end select-none"
					style="height: {PLOT_PX + 4}px; width: {width}px; gap: {GAP_PX}px; cursor: {dragging
						? 'grabbing'
						: 'pointer'}"
					onpointermove={move}
					onpointerleave={leave}
					onpointerdown={down}
					onpointerup={up}
					onpointercancel={() => (dragging = false)}
				>
					{#each runs as point, i (point.scan_id)}
						<div
							class="flex shrink-0 flex-col-reverse gap-px rounded-[1px] {ring(i)}"
							style="width: {px}px"
						>
							{#if !observed(i)}
								<span class="block rounded-[2px] {HATCH}" style="height: {UNOBSERVED_PX}px"></span>
							{:else}
								{#each stack as severity (severity)}
									{#if point.open[severity]}
										<span
											class="block rounded-[1px]"
											style="height: {height(point.open[severity])}px; background: {SEVERITY_FILL[
												severity
											]}"
										></span>
									{/if}
								{/each}
								{#if !total(point)}
									<span class="block h-px bg-border"></span>
								{/if}
							{/if}
						</div>
					{/each}
					{#if hovered >= 0}
						<span
							bind:this={anchor}
							class="pointer-events-none absolute inset-y-0"
							style="left: {hovered * step}px; width: {px}px"
							aria-hidden="true"
						></span>
					{/if}
				</div>
			{/snippet}
		</Tooltip.Trigger>
		{#if shown && anchor && hovered >= 0}
			<Tooltip.Content
				customAnchor={anchor}
				side="top"
				sideOffset={8}
				class="w-64 rounded-lg border bg-popover p-3 text-xs text-popover-foreground shadow-md"
				arrowClasses="hidden"
			>
				<div class="flex flex-col gap-1.5">
					<div class="flex items-baseline justify-between gap-3">
						<span class="font-medium">
							{formatDateTime(scans[hovered]?.started_at ?? '')}
						</span>
						<span class="text-muted-foreground">run {hovered + 1} of {n}</span>
					</div>
					{#if !observed(hovered)}
						<div class="text-muted-foreground">
							{FINDING_OBSERVATION_LABELS[Observation.UNOBSERVED]}
						</div>
					{:else}
						<div class="flex justify-between gap-3">
							<span class="text-muted-foreground">Open</span>
							<span class="text-right">
								{total(shown)}{breakdown(shown) ? ` · ${breakdown(shown)}` : ''}
							</span>
						</div>
						{#if shown.fixed}
							<div class="flex justify-between gap-3">
								<span class="text-muted-foreground">Fixed in this run</span>
								<span>{shown.fixed}</span>
							</div>
						{/if}
						{#if shown.regressed}
							<div class="flex justify-between gap-3">
								<span class="text-muted-foreground">Came back</span>
								<span>{shown.regressed}</span>
							</div>
						{/if}
						{#if tested(shown)}
							<div class="flex justify-between gap-3">
								<span class="text-muted-foreground">Tested</span>
								<span class="text-right">{tested(shown)}</span>
							</div>
						{/if}
						{#if scans[hovered]?.observation === Observation.PARTIAL}
							<div class="text-muted-foreground">
								{FINDING_OBSERVATION_LABELS[Observation.PARTIAL]}
							</div>
						{/if}
					{/if}
				</div>
			</Tooltip.Content>
		{/if}
	</Tooltip.Root>
	<div class="relative h-4 text-2xs text-muted-foreground tabular-nums" style="width: {width}px">
		{#each labels as label (label.index)}
			<button
				type="button"
				class="absolute bottom-0 rounded-sm whitespace-nowrap outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/70 {shiftClass(
					label.align
				)} {label.index === last ? 'text-foreground' : ''}"
				style="left: {label.x}px"
				disabled={label.index === last}
				onclick={() => onOpenScan(scans[label.index].id)}
			>
				{label.text || formatMonthDay(scans[label.index].started_at ?? '')}
			</button>
		{/each}
	</div>
</div>
