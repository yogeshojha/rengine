<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import Hint from '$lib/components/hint.svelte';
	import {
		FINDING_STATE_LABELS,
		FindingGroup,
		FindingState,
		PRESENT_STATES
	} from '$lib/config/timeline';
	import { SEVERITY_CHIP, SEVERITY_FILL, severityLabel } from '$lib/config/vulnerabilities';
	import { VULN_STATE_LABELS } from '$lib/config/vulnerabilities';
	import { EVIDENCE_HELP, EVIDENCE_LABELS, Evidence } from '$lib/config/evidence';
	import { shortKey } from '$lib/config/issue-trackers';
	import type { FindingLifespan, TimelineScan } from '$lib/types/timeline';
	import { formatMonthDay, relativeTimeLong } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { rowTone } from '../../table/columns';
	import LifespanTrack from './lifespan-track.svelte';
	import { WHO_PX, STATUS_PX } from './columns';

	interface Props {
		item: FindingLifespan;
		scans: TimelineScan[];
		index: number;
		focused: boolean;
		selected: boolean;
		pad: string;
		highlight: number;
		onHover: (index: number) => void;
		onOpen: () => void;
		onOpenScan: (scanId: string) => void;
	}

	let {
		item,
		scans,
		index,
		focused,
		selected,
		pad,
		highlight,
		onHover,
		onOpen,
		onOpenScan
	}: Props = $props();

	let v = $derived(item.finding);
	let sev = $derived(v.severity);
	let chip = $derived(SEVERITY_CHIP[sev] ?? SEVERITY_CHIP.unknown);
	let fill = $derived(SEVERITY_FILL[sev] ?? SEVERITY_FILL.unknown);
	let location = $derived(v.host ? (v.port ? `${v.host}:${v.port}` : v.host) : (v.ip ?? ''));
	let present = $derived(PRESENT_STATES.includes(item.state));
	let lastFound = $derived.by(() => {
		const seg = [...item.segments].reverse().find((s) => PRESENT_STATES.includes(s.state));
		const at = seg ? scans[seg.end]?.started_at : null;
		return at ? formatMonthDay(at) : '';
	});
	let ticket = $derived(v.tickets?.[0] ?? null);

	let pill = $derived.by(() => {
		const days = item.open_days ?? 0;
		switch (item.group) {
			case FindingGroup.SET_ASIDE:
				return `Set aside · ${(VULN_STATE_LABELS[item.triage_state] ?? item.triage_state).toLowerCase()}`;
			case FindingGroup.NEW:
				return 'Open · new';
			default:
				break;
		}
		if (item.state === FindingState.REGRESSED) return `Open again · ${days} d`;
		if (item.state === FindingState.FIXED && item.fixed_at)
			return `Fixed · ${formatMonthDay(item.fixed_at)}`;
		if (present) return `Open · ${days} d`;
		return `Open · not tested ${plural(item.not_tested_runs, 'run')}`;
	});
	let sub = $derived.by(() => {
		switch (item.group) {
			case FindingGroup.SET_ASIDE:
				return 'Not counted as open';
			case FindingGroup.NEW:
				return item.tested_runs > 1
					? `web asset tested in ${plural(item.tested_runs - 1, 'earlier run')}`
					: 'first time on this target';
			case FindingGroup.FIXED:
				return item.fixed_at ? relativeTimeLong(item.fixed_at) : '';
			default:
				break;
		}
		if (item.state === FindingState.REGRESSED) {
			if (ticket && ticket.external_key)
				return `issue ${shortKey(ticket.external_key)} ${ticket.remote_status ?? ticket.state}`;
			return item.regressions > 1
				? `came back ${plural(item.regressions, 'time')}`
				: item.returned_at
					? `came back ${formatMonthDay(item.returned_at)}`
					: '';
		}
		if (item.state === FindingState.FIXED)
			return item.regressions === 1
				? 'came back once'
				: `came back ${plural(item.regressions, 'time')}`;
		if (!present) return lastFound ? `last found ${lastFound}` : FINDING_STATE_LABELS[item.state];
		if (!item.open_since) return '';
		const start = scans[0]?.started_at;
		const earlier = start ? new Date(item.open_since) < new Date(start) : false;
		const seen =
			item.first_seen_at && new Date(item.first_seen_at) < new Date(item.open_since)
				? ` · first seen ${formatMonthDay(item.first_seen_at)}`
				: '';
		return `since ${formatMonthDay(item.open_since)}${earlier ? ' · before the window' : seen}`;
	});
	let pillClass = $derived.by(() => {
		if (item.group === FindingGroup.SET_ASIDE) return 'bg-muted text-muted-foreground';
		if (item.state === FindingState.FIXED) return 'bg-muted text-foreground';
		if (!present) return 'bg-muted text-muted-foreground';
		return chip.chip;
	});
</script>

<div
	role="row"
	tabindex="-1"
	data-vuln-row-index={index}
	class="group flex items-stretch outline-none {rowTone(selected, focused)}"
>
	<span class="w-1 shrink-0" style="background: {fill}" aria-hidden="true"></span>
	<div class="flex min-w-0 flex-1 items-center gap-6 pr-4 pl-3 {pad}">
		<div class="min-w-0 shrink-0" style="width: {WHO_PX}px">
			<button
				type="button"
				class="block max-w-full truncate text-left text-sm font-semibold outline-none hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/70"
				onclick={() => onOpen()}
			>
				{v.template_name}
			</button>
			<div class="mt-1 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
				{#if location}<code class="truncate font-mono text-2xs">{location}</code>{/if}
				<span class="shrink-0 rounded px-1 text-2xs font-semibold {chip.chip}">
					{severityLabel(sev)}
				</span>
				{#if v.evidence === Evidence.PROVEN}
					<Hint text={EVIDENCE_HELP[Evidence.PROVEN]}>
						{#snippet child(props)}
							<span
								{...props}
								class="shrink-0 rounded px-1 text-2xs font-semibold ring-1 ring-foreground/40 ring-inset"
								>{EVIDENCE_LABELS[Evidence.PROVEN]}</span
							>
						{/snippet}
					</Hint>
				{/if}
				{#if v.is_kev}
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
		<LifespanTrack {item} {scans} {highlight} {onHover} {onOpen} {onOpenScan} />
		<div class="ml-auto shrink-0 text-right" style="width: {STATUS_PX}px">
			<span
				class="inline-flex h-6 items-center rounded-full px-2.5 text-xs font-semibold whitespace-nowrap {pillClass}"
			>
				{pill}
			</span>
			{#if sub}<div class="mt-1 truncate text-2xs text-muted-foreground">{sub}</div>{/if}
		</div>
	</div>
</div>
