<script lang="ts">
	import {
		KIND_LABELS,
		NewKind,
		Signal,
		type NewKindKey,
		type SignalKey
	} from '$lib/config/whats-new';
	import { Severity, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import type { NewDay } from '$lib/types/whats-new';

	interface Props {
		days: NewDay[];
		kinds: NewKindKey[];
		counts: Record<string, number>;
		periodStart: string | null;
		periodEnd: string | null;
		markedAt: string | null;
		from: string | null;
		to: string | null;
		active: SignalKey | null;
		onPick: (from: string | null, to: string | null) => void;
		onSignal: (signal: SignalKey | null) => void;
	}

	let {
		days,
		kinds,
		counts,
		periodStart,
		periodEnd,
		markedAt,
		from,
		to,
		active,
		onPick,
		onSignal
	}: Props = $props();

	const LANE = 30;
	const AXIS = 20;
	const WIDE = 560;
	const DAY_MS = 86_400_000;

	let width = $state(0);
	let span = $derived(width >= WIDE ? 30 : 14);
	let shown = $derived(days.slice(-span));
	let lanes = $derived(kinds.filter((k) => shown.some((d) => (d.counts[k] ?? 0) > 0)));
	let cw = $derived(shown.length ? width / shown.length : 0);
	let height = $derived(lanes.length * LANE + AXIS);
	let peaks = $derived(
		Object.fromEntries(
			lanes.map((k) => [k, Math.max(1, ...shown.map((d) => d.counts[k] ?? 0))])
		) as Record<string, number>
	);

	let hover = $state<number | null>(null);
	let anchor = $state<number | null>(null);
	let dragging = $state(false);

	const cx = (i: number) => cw * (i + 0.5);
	const today = () => new Date().toLocaleDateString('en-CA');

	function position(iso: string | null): number | null {
		if (!iso || !shown.length) return null;
		const at = new Date(iso);
		const key = at.toLocaleDateString('en-CA');
		const index = shown.findIndex((d) => d.date === key);
		if (index < 0) return key < shown[0].date ? 0 : null;
		const midnight = new Date(`${key}T00:00:00`).getTime();
		return cw * (index + Math.min(1, (at.getTime() - midnight) / DAY_MS));
	}
	let periodX = $derived(position(periodStart));
	let periodEndX = $derived(periodEnd ? position(periodEnd) : width);
	let markX = $derived(position(markedAt));

	let range = $derived.by<[number, number] | null>(() => {
		if (dragging && anchor !== null && hover !== null) {
			return anchor <= hover ? [anchor, hover] : [hover, anchor];
		}
		if (!from) return null;
		const a = shown.findIndex((d) => d.date === from);
		const b = shown.findIndex((d) => d.date === (to ?? from));
		if (a < 0 && b < 0) return null;
		return [Math.max(0, a), b < 0 ? shown.length - 1 : b];
	});

	function radius(kind: string, n: number): number {
		if (!n) return 0;
		return 3.5 + 6.5 * Math.sqrt(n / peaks[kind]);
	}
	function fill(kind: string, day: NewDay): string {
		if (kind !== NewKind.FINDING) return 'var(--series)';
		return (day.counts[Severity.CRITICAL] ?? 0) > 0 ? 'var(--sev-critical)' : 'var(--sev-high)';
	}
	function dayAt(e: PointerEvent): number {
		const box = (e.currentTarget as SVGElement).getBoundingClientRect();
		const i = Math.floor((e.clientX - box.left) / cw);
		return Math.max(0, Math.min(shown.length - 1, i));
	}
	function down(e: PointerEvent) {
		if (e.button !== 0) return;
		(e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
		anchor = dayAt(e);
		hover = anchor;
		dragging = true;
	}
	function move(e: PointerEvent) {
		hover = dayAt(e);
	}
	function up() {
		if (!dragging || anchor === null || hover === null) return;
		const [lo, hi] = anchor <= hover ? [anchor, hover] : [hover, anchor];
		dragging = false;
		anchor = null;
		const a = shown[lo].date;
		const b = shown[hi].date;
		if (lo === hi && from === a && !to) onPick(null, null);
		else onPick(a, lo === hi ? null : b);
	}
	function label(date: string, long = false): string {
		if (date === today()) return 'Today';
		return new Date(`${date}T12:00:00`).toLocaleDateString('en-US', {
			...(long ? { weekday: 'short' } : {}),
			month: 'short',
			day: 'numeric'
		});
	}
	let ticks = $derived(
		shown
			.map((d, i) => ({ d, i }))
			.filter(({ i }) => (shown.length - 1 - i) % (span === 30 ? 7 : 4) === 0)
	);
	let hovered = $derived(hover !== null ? shown[hover] : null);
	let tipRows = $derived.by(() => {
		const day = hovered;
		if (!day) return [];
		const rows: { key: string; label: string; n: number; color: string }[] = [];
		for (const kind of lanes) {
			if (kind === NewKind.FINDING) {
				for (const sev of [Severity.CRITICAL, Severity.HIGH]) {
					const n = day.counts[sev] ?? 0;
					if (n)
						rows.push({ key: sev, label: SEVERITY_LABELS[sev], n, color: `var(--sev-${sev})` });
				}
			} else if (day.counts[kind]) {
				rows.push({
					key: kind,
					label: KIND_LABELS[kind],
					n: day.counts[kind],
					color: 'var(--series)'
				});
			}
		}
		return rows;
	});
	let tipLeft = $derived(hover === null ? 0 : Math.max(0, Math.min(width - 188, cx(hover) - 94)));
</script>

<div class="flex min-w-0 flex-1 gap-3">
	<div class="flex w-24 shrink-0 flex-col sm:w-28" style="padding-bottom: {AXIS}px">
		{#each lanes as kind (kind)}
			{@const on = active === kind}
			<button
				type="button"
				class="-ml-1.5 flex items-center justify-between gap-2 rounded-md px-1.5 text-left text-xs transition-colors {on
					? 'bg-muted text-foreground'
					: 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'}"
				style="height: {LANE}px"
				aria-pressed={on}
				onclick={() => onSignal(on ? null : kind)}
			>
				<span>{KIND_LABELS[kind]}</span>
				<span class="font-mono font-medium tabular-nums {counts[kind] ? 'text-foreground' : ''}"
					>{(counts[kind] ?? 0).toLocaleString()}</span
				>
			</button>
		{/each}
	</div>

	<div class="relative min-w-0 flex-1" bind:clientWidth={width}>
		{#if lanes.length === 0}
			<div
				class="flex items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground"
				style="height: {LANE * 2}px"
			>
				No events in {span} days
			</div>
		{:else if width > 0}
			<svg
				{width}
				{height}
				class="block touch-none select-none"
				role="img"
				aria-label="Events per day, last {span} days"
				onpointerdown={down}
				onpointermove={move}
				onpointerup={up}
				onpointerleave={() => {
					if (!dragging) hover = null;
				}}
			>
				{#if periodX !== null && !range}
					<rect
						x={periodX}
						y="0"
						width={Math.max(0, (periodEndX ?? width) - periodX)}
						height={lanes.length * LANE}
						rx="6"
						style="fill: var(--primary); opacity: 0.06"
					/>
				{/if}

				{#each lanes as kind, li (kind)}
					<rect
						x="0"
						y={li * LANE + 7}
						{width}
						height={LANE - 14}
						rx={(LANE - 14) / 2}
						style="fill: var(--muted); opacity: 0.7"
					/>
				{/each}

				{#if range}
					<rect
						x={range[0] * cw}
						y="0"
						width={(range[1] - range[0] + 1) * cw}
						height={lanes.length * LANE}
						rx="6"
						style="fill: var(--foreground); opacity: 0.07"
					/>
					<rect
						x={range[0] * cw + 0.5}
						y="0.5"
						width={(range[1] - range[0] + 1) * cw - 1}
						height={lanes.length * LANE - 1}
						rx="6"
						style="fill: none; stroke: var(--foreground); stroke-opacity: 0.35"
					/>
				{/if}

				{#if hover !== null}
					<line
						x1={cx(hover)}
						x2={cx(hover)}
						y1="0"
						y2={lanes.length * LANE}
						style="stroke: var(--foreground); stroke-opacity: 0.25"
						stroke-dasharray="2 3"
					/>
				{/if}

				{#if markX !== null}
					<line
						x1={markX}
						x2={markX}
						y1="-2"
						y2={lanes.length * LANE + 2}
						style="stroke: var(--muted-foreground)"
						stroke-width="1.5"
						stroke-dasharray="4 3"
					/>
				{/if}

				{#each lanes as kind, li (kind)}
					{#each shown as day, i (day.date)}
						{@const n = day.counts[kind] ?? 0}
						{#if n}
							<circle
								cx={cx(i)}
								cy={li * LANE + LANE / 2}
								r={radius(kind, n)}
								style="fill: {fill(
									kind,
									day
								)}; stroke: var(--card); stroke-width: 2; opacity: {active &&
								active !== kind &&
								!(
									kind === NewKind.FINDING &&
									(active === Signal.CRITICAL || active === Signal.HIGH)
								)
									? 0.3
									: kind === NewKind.FINDING
										? 1
										: 0.75}"
							/>
						{/if}
					{/each}
				{/each}

				{#each ticks as { d, i } (d.date)}
					<text
						x={i === shown.length - 1 ? width : cx(i)}
						y={lanes.length * LANE + 14}
						text-anchor={i === shown.length - 1 ? 'end' : 'middle'}
						class="text-2xs"
						style="fill: var(--muted-foreground)">{label(d.date)}</text
					>
				{/each}
			</svg>

			{#if hovered && hover !== null && !dragging}
				<div
					class="pointer-events-none absolute z-20 w-[11.75rem] rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md"
					style="left: {tipLeft}px; top: {lanes.length * LANE + 6}px"
				>
					<div class="mb-1 font-medium">{label(hovered.date, true)}</div>
					{#each tipRows as row (row.key)}
						<div class="flex items-center justify-between gap-2 py-0.5">
							<span class="flex items-center gap-1.5 text-muted-foreground">
								<span class="size-2 rounded-full" style="background: {row.color}"></span>
								{row.label}
							</span>
							<span class="font-mono tabular-nums">{row.n.toLocaleString()}</span>
						</div>
					{:else}
						<div class="text-muted-foreground">Nothing new</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>
