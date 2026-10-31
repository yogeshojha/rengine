<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import {
		FINDING_OBSERVATION_LABELS,
		FINDING_STATE_LABELS,
		FindingState,
		Observation,
		PRESENT_STATES,
		SEGMENT_DASH,
		SEGMENT_HATCH
	} from '$lib/config/timeline';
	import { ROUTES } from '$lib/config/routes';
	import { SEVERITY_FILL } from '$lib/config/vulnerabilities';
	import { EVIDENCE_LABELS } from '$lib/config/evidence';
	import { VULN_STATE_LABELS, VulnState } from '$lib/config/vulnerabilities';
	import { shortKey } from '$lib/config/issue-trackers';
	import type { FindingLifespan, LifeSegment, TimelineScan } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { columnAt, columnLeft, columnWidth, dayCount, trackWidth } from './geometry';

	interface Props {
		item: FindingLifespan;
		scans: TimelineScan[];
		/** the column every track highlights */
		highlight?: number;
		onHover?: (index: number) => void;
		onOpen: () => void;
		onOpenScan: (scanId: string) => void;
	}

	let { item, scans, highlight = -1, onHover, onOpen, onOpenScan }: Props = $props();

	const CLOSE_MS = 160;
	const LABEL_MIN_PX = 64;

	let n = $derived(scans.length);
	let width = $derived(trackWidth(n));
	let col = $derived(columnWidth(n, width));
	let last = $derived(n - 1);
	let fill = $derived(SEVERITY_FILL[item.finding.severity] ?? SEVERITY_FILL.unknown);

	let hovered = $state(-1);
	let open = $state(false);
	let anchor = $state<HTMLElement | null>(null);
	let closing: ReturnType<typeof setTimeout> | null = null;

	function left(seg: LifeSegment): number {
		return columnLeft(seg.start, n, width);
	}
	function span(seg: LifeSegment): number {
		return (seg.end - seg.start + 1) * col;
	}
	function label(seg: LifeSegment): string {
		if (span(seg) < LABEL_MIN_PX) return '';
		const days = seg.days ?? 0;
		switch (seg.state) {
			case FindingState.OPEN:
			case FindingState.REGRESSED:
				return `open ${dayCount(days)}`;
			case FindingState.FIXED:
				return `fixed ${dayCount(days)}`;
			case FindingState.NOT_TESTED:
				return 'not tested';
			default:
				return 'no scan';
		}
	}
	function present(state: FindingState): boolean {
		return PRESENT_STATES.includes(state);
	}
	function segmentStyle(seg: LifeSegment): string {
		const base = `left:${left(seg)}px;width:${span(seg)}px;`;
		if (present(seg.state)) return `${base}top:14px;height:12px;background:${fill}`;
		if (seg.state === FindingState.FIXED)
			return `${base}top:17px;height:6px;background:${SEGMENT_DASH}`;
		return `${base}top:15px;height:10px;background:${SEGMENT_HATCH};opacity:${seg.state === FindingState.UNOBSERVED ? 0.6 : 1}`;
	}

	function track(e: MouseEvent) {
		const rect = e.currentTarget as HTMLElement;
		const i = columnAt(e.clientX - rect.getBoundingClientRect().left, n, width);
		if (i !== hovered) {
			hovered = i;
			onHover?.(i);
		}
		if (closing) clearTimeout(closing);
		closing = null;
		open = true;
	}
	function leave() {
		onHover?.(-1);
		closing = setTimeout(() => {
			open = false;
			hovered = -1;
		}, CLOSE_MS);
	}
	function hold() {
		if (closing) clearTimeout(closing);
		closing = null;
	}
	function release() {
		open = false;
		hovered = -1;
	}

	let shownState = $derived(hovered >= 0 ? item.cells[hovered]?.state : null);
	let shownScan = $derived(hovered >= 0 ? scans[hovered] : null);
	let before = $derived.by(() => {
		if (hovered < 0) return '';
		const at = item.segments.findIndex((s) => s.start <= hovered && hovered <= s.end);
		if (at < 0) return 'Not seen before';
		if (at === 0) return 'First run with the finding';
		const prev = item.segments[at - 1];
		const since = scans[prev.start]?.started_at;
		const name = FINDING_STATE_LABELS[prev.state];
		return since
			? `${name} since ${formatMonthDay(since)} · ${dayCount(prev.days ?? 0)}`
			: `${name} · ${dayCount(prev.days ?? 0)}`;
	});
	let headline = $derived.by(() => {
		if (!shownState || !shownScan) return '';
		const parts = [FINDING_STATE_LABELS[shownState]];
		if (shownState === FindingState.NOT_TESTED && shownScan.observation !== Observation.OBSERVED) {
			parts.push(FINDING_OBSERVATION_LABELS[shownScan.observation]);
		}
		if (hovered === last) parts.push('This scan');
		return parts.join(' · ');
	});
	let ticket = $derived(item.finding.tickets?.[0] ?? null);
	let evidence = $derived(
		[
			EVIDENCE_LABELS[item.finding.evidence] ?? item.finding.evidence,
			item.finding.is_kev ? 'known exploited' : ''
		]
			.filter(Boolean)
			.join(' · ')
	);
	let summary = $derived(
		`${item.finding.template_name}: ${FINDING_STATE_LABELS[item.state]}, ${plural(item.regressions, 'regression')} over ${plural(n, 'run')}`
	);
</script>

<Tooltip.Root bind:open>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
			<div
				{...props}
				role="img"
				aria-label={summary}
				class="relative h-9 shrink-0"
				style="width: {width}px"
				onmousemove={track}
				onmouseleave={leave}
				onclick={() => onOpen()}
			>
				<span class="absolute inset-x-0 top-5 h-px bg-border" aria-hidden="true"></span>
				{#each item.segments as seg (seg.start)}
					<span class="absolute rounded-[6px]" style={segmentStyle(seg)}>
						{#if label(seg)}
							<span
								class="absolute -top-[14px] left-1 text-2xs font-medium whitespace-nowrap text-muted-foreground"
							>
								{label(seg)}
							</span>
						{/if}
						{#if seg.state === FindingState.REGRESSED}
							<span
								class="absolute top-1/2 -left-1 size-3.5 -translate-y-1/2 rounded-full bg-card ring-2 ring-destructive"
								aria-hidden="true"
							></span>
						{/if}
					</span>
				{/each}
				{#if highlight >= 0 && highlight < n}
					<span
						class="absolute top-1 bottom-1 w-px bg-foreground/50"
						style="left: {columnLeft(highlight, n, width) + col / 2}px"
						aria-hidden="true"
					></span>
				{/if}
				<span
					class="absolute top-2 right-0 bottom-2 w-0.5 rounded-sm bg-foreground"
					aria-hidden="true"
				></span>
				{#if hovered >= 0}
					<span
						bind:this={anchor}
						class="pointer-events-none absolute inset-y-0"
						style="left: {columnLeft(hovered, n, width)}px; width: {col}px"
						aria-hidden="true"
					></span>
				{/if}
			</div>
		{/snippet}
	</Tooltip.Trigger>
	{#if hovered >= 0 && shownScan && anchor}
		<Tooltip.Content
			customAnchor={anchor}
			side="top"
			sideOffset={8}
			class="w-[26rem] rounded-lg border bg-popover p-3 text-popover-foreground shadow-md"
			arrowClasses="hidden"
			onmouseenter={hold}
			onmouseleave={release}
		>
			<div class="flex flex-col gap-2 text-xs">
				<div class="flex items-baseline justify-between gap-4">
					<span class="font-medium">
						{shownScan.started_at ? formatDateTime(shownScan.started_at) : ''} · run {hovered + 1} of
						{n}
					</span>
					<span class="text-muted-foreground">{headline}</span>
				</div>
				<dl class="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1.5">
					<dt class="text-muted-foreground">Before</dt>
					<dd class="min-w-0 truncate">{before}</dd>
					<dt class="text-muted-foreground">Matched at</dt>
					<dd class="min-w-0 truncate font-mono text-2xs">{item.finding.matched_at}</dd>
					<dt class="text-muted-foreground">Evidence</dt>
					<dd class="min-w-0 truncate">{evidence}</dd>
					{#if ticket}
						<dt class="text-muted-foreground">Issue</dt>
						<dd class="min-w-0 truncate">
							{ticket.external_key ? shortKey(ticket.external_key) : ticket.tracker_name} · {ticket.remote_status ??
								ticket.state}
						</dd>
					{/if}
					{#if item.triage_state !== VulnState.OPEN}
						<dt class="text-muted-foreground">Reviewed</dt>
						<dd class="min-w-0 truncate">
							{VULN_STATE_LABELS[item.triage_state] ?? item.triage_state}
						</dd>
					{/if}
				</dl>
				<div class="flex flex-wrap items-center gap-2 border-t pt-2">
					<Button size="sm" variant="outline" class="h-7 text-xs" onclick={() => onOpen()}>
						Open the finding
					</Button>
					{#if hovered !== last}
						<Button
							size="sm"
							variant="ghost"
							class="h-7 text-xs"
							onclick={() => onOpenScan(shownScan.id)}
						>
							Open this run
						</Button>
					{/if}
					{#if hovered > 0}
						<Button
							size="sm"
							variant="ghost"
							class="h-7 text-xs"
							href={ROUTES.compare(shownScan.id, scans[hovered - 1].id)}
						>
							Compare with run before
						</Button>
					{/if}
				</div>
			</div>
		</Tooltip.Content>
	{/if}
</Tooltip.Root>
