<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import {
		FINDING_GROUP_HELP,
		FINDING_GROUP_LABELS,
		FINDING_GROUP_ORDER,
		FindingGroup,
		SEGMENT_DASH,
		SEGMENT_HATCH
	} from '$lib/config/timeline';
	import { SEVERITY_FILL, Severity } from '$lib/config/vulnerabilities';
	import type { FindingLifespan, FindingTimelineResult } from '$lib/types/timeline';
	import { formatDateTime, formatMonthDay } from '$lib/utilities/dates';
	import LifespanCard from './lifespan-card.svelte';
	import StatsBand from './stats-band.svelte';
	import { STATUS_PX, WHO_PX } from './columns';
	import { axisLabels, columnLeft, columnWidth, shiftClass, trackWidth } from './geometry';

	interface Props {
		result: FindingTimelineResult;
		loading: boolean;
		focusedIndex: number;
		selectedId: string | null;
		pad: string;
		onOpen: (item: FindingLifespan) => void;
		/** opens the findings Timeline of an earlier run */
		onOpenScan: (scanId: string) => void;
		track: (node: HTMLElement) => void | (() => void);
	}

	let { result, loading, focusedIndex, selectedId, pad, onOpen, onOpenScan, track }: Props =
		$props();

	let scans = $derived(result.scans);
	let n = $derived(scans.length);
	let last = $derived(n - 1);
	let width = $derived(trackWidth(n));
	let labels = $derived(axisLabels(scans, width));
	let highlight = $state(-1);
	let windowNote = $derived(
		result.runs > n && scans[0]?.started_at
			? `Last ${n} of ${result.runs} runs · earlier runs open from ${formatMonthDay(scans[0].started_at)}`
			: ''
	);

	const GROUP_DOT: Record<FindingGroup, string> = {
		[FindingGroup.REGRESSED]: 'bg-destructive',
		[FindingGroup.NEW]: 'bg-primary',
		[FindingGroup.OPEN]: 'bg-foreground',
		[FindingGroup.FIXED]: 'bg-fill-strong',
		[FindingGroup.SET_ASIDE]: 'bg-fill-muted'
	};

	let sections = $derived(
		FINDING_GROUP_ORDER.map((group) => ({
			group,
			items: result.items.filter((i) => i.group === group)
		})).filter((s) => s.items.length)
	);
	let offsets = $derived.by(() => {
		const out: Record<string, number> = {};
		let i = 0;
		for (const s of sections) {
			out[s.group] = i;
			i += s.items.length;
		}
		return out;
	});

	function scanHint(i: number): string {
		const at = scans[i]?.started_at;
		const when = at ? formatDateTime(at) : '';
		return i === last ? `${when} · This scan` : `${when} · Open this run's findings`;
	}
	function count(group: FindingGroup): string {
		const total = result.counts[group] ?? 0;
		const shown = sections.find((s) => s.group === group)?.items.length ?? 0;
		return shown < total ? `${shown} of ${total}` : String(total);
	}
</script>

{#if result.stats}
	<StatsBand
		stats={result.stats}
		{scans}
		runs={result.runs}
		{highlight}
		onHover={(i) => (highlight = i)}
		{onOpenScan}
	/>
{/if}

<ScrollArea orientation="horizontal">
	<div
		class="flex items-end gap-6 border-b bg-muted/20 py-2 pr-4 pl-4 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
	>
		<div class="shrink-0" style="width: {WHO_PX}px">Finding</div>
		<div class="relative h-4 shrink-0 normal-case tabular-nums" style="width: {width}px">
			{#each labels as label (label.index)}
				<Hint text={scanHint(label.index)}>
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="absolute bottom-0 rounded-sm whitespace-nowrap outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/70 {shiftClass(
								label.align
							)} {label.index === last || highlight === label.index ? 'text-foreground' : ''}"
							style="left: {label.x}px"
							disabled={label.index === last}
							onmouseenter={() => (highlight = label.index)}
							onmouseleave={() => (highlight = -1)}
							onclick={() => onOpenScan(scans[label.index].id)}
						>
							{label.text}
						</button>
					{/snippet}
				</Hint>
			{/each}
			{#if highlight >= 0 && highlight < n && !labels.some((l) => Math.abs(l.index - highlight) < 3)}
				<span
					class="absolute bottom-0 -translate-x-1/2 rounded-sm bg-foreground px-1 text-background normal-case"
					style="left: {columnLeft(highlight, n, width) + columnWidth(n, width) / 2}px"
				>
					{formatMonthDay(scans[highlight].started_at ?? '')}
				</span>
			{/if}
		</div>
		<div class="ml-auto shrink-0 text-right" style="width: {STATUS_PX}px">Status</div>
	</div>

	<div class="transition-opacity {loading ? 'opacity-60' : ''}" role="rowgroup" {@attach track}>
		{#each sections as section (section.group)}
			<div
				class="flex items-center gap-2.5 border-b border-border/50 bg-muted/10 px-4 pt-4 pb-2 text-xs font-semibold"
			>
				<span class="size-2 rounded-full {GROUP_DOT[section.group]}" aria-hidden="true"></span>
				<span>{FINDING_GROUP_LABELS[section.group]}</span>
				<span class="font-medium text-muted-foreground">
					{count(section.group)} · {FINDING_GROUP_HELP[section.group]}
				</span>
			</div>
			<div class="divide-y divide-border/50">
				{#each section.items as item, i (item.finding.fingerprint)}
					{@const index = (offsets[section.group] ?? 0) + i}
					<LifespanCard
						{item}
						{scans}
						{index}
						focused={focusedIndex === index}
						selected={selectedId === item.finding.id}
						{pad}
						{highlight}
						onHover={(col) => (highlight = col)}
						onOpen={() => onOpen(item)}
						{onOpenScan}
					/>
				{/each}
			</div>
		{/each}
	</div>
</ScrollArea>

<div
	class="flex flex-wrap items-center gap-x-1 gap-y-1 border-t px-2 py-1.5 text-xs text-muted-foreground"
>
	<span class="flex items-center gap-1.5 px-2 py-1">
		{#each [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW] as sev (sev)}
			<span
				class="h-2.5 w-3 rounded-[3px]"
				style="background: {SEVERITY_FILL[sev]}"
				aria-hidden="true"
			></span>
		{/each}
		Open, by severity
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="h-1.5 w-5 rounded-[2px]" style="background: {SEGMENT_DASH}" aria-hidden="true"
		></span>
		Fixed
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="h-2.5 w-5 rounded-[3px]" style="background: {SEGMENT_HATCH}" aria-hidden="true"
		></span>
		Not tested
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="size-3 rounded-full bg-card ring-2 ring-destructive" aria-hidden="true"></span>
		Came back
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="h-3 w-0.5 rounded-sm bg-foreground" aria-hidden="true"></span>
		This scan
	</span>
	<span class="ml-auto flex flex-wrap items-center gap-x-3 px-2 py-1">
		{#if windowNote}<span>{windowNote}</span>{/if}
		<span>J K move · Enter opens the finding · ← opens the run before</span>
	</span>
</div>
