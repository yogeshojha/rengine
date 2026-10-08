<script lang="ts">
	import type { ScanDay } from '$lib/types/scan';
	import { SEVERITY_CHIP } from '$lib/config/vulnerabilities';
	import { formatShortDate } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { historyPrefs } from './prefs.svelte';

	const DAY_MS = 86_400_000;

	interface Props {
		days: ScanDay[];
		from: string | null;
		to: string | null;
		onRange: (from: string | null, to: string | null) => void;
	}

	let { days, from, to, onRange }: Props = $props();

	let max = $derived(Math.max(1, ...days.map((d) => d.runs)));
	let hover = $state<number | null>(null);
	let drag = $state<{ a: number; b: number } | null>(null);
	let el = $state<HTMLDivElement | null>(null);

	let fromT = $derived(from ? new Date(from).getTime() : null);
	let toT = $derived(to ? new Date(to).getTime() : null);
	const inRange = (d: ScanDay) => {
		const t = new Date(d.day).getTime();
		return fromT != null && t >= fromT - 1 && (toT == null || t < toT);
	};
	let selected = $derived(fromT != null);

	function indexAt(clientX: number): number {
		if (!el) return 0;
		const r = el.getBoundingClientRect();
		return Math.max(
			0,
			Math.min(days.length - 1, Math.floor(((clientX - r.left) / r.width) * days.length))
		);
	}

	function commit(a: number, b: number) {
		const lo = Math.min(a, b);
		const hi = Math.max(a, b);
		const start = new Date(days[lo].day).getTime();
		onRange(
			new Date(start).toISOString(),
			new Date(new Date(days[hi].day).getTime() + DAY_MS).toISOString()
		);
	}

	function worst(d: ScanDay): string | null {
		for (const s of historyPrefs.severities)
			if (d[s as 'critical' | 'high' | 'medium'] > 0) return s;
		return null;
	}

	const STEP: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1 };

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			e.stopPropagation();
			if (hover != null && days.length) commit(drag?.a ?? hover, hover);
			drag = null;
			return;
		}
		if (!days.length) return;
		const last = days.length - 1;
		const step = STEP[e.key];
		if (step) {
			e.preventDefault();
			const at = hover ?? (step > 0 ? -1 : last + 1);
			const next = Math.max(0, Math.min(last, at + step));
			drag = e.shiftKey ? { a: drag?.a ?? hover ?? next, b: next } : null;
			hover = next;
		} else if (e.key === 'Escape' && (hover != null || drag)) {
			e.stopPropagation();
			hover = null;
			drag = null;
		}
	}

	let tip = $derived(hover != null ? days[hover] : null);
</script>

<div class="flex min-w-0 flex-col gap-1">
	<!-- svelte-ignore a11y_no_static_element_interactions, a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
	<div
		bind:this={el}
		tabindex="0"
		class="relative flex h-14 cursor-crosshair touch-none items-end gap-[2px] rounded-sm outline-none select-none focus-visible:ring-[3px] focus-visible:ring-ring/70"
		onpointerdown={(e) => {
			const i = indexAt(e.clientX);
			drag = { a: i, b: i };
			(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		}}
		onpointermove={(e) => {
			const i = indexAt(e.clientX);
			hover = i;
			if (drag) drag = { ...drag, b: i };
		}}
		onpointerup={() => {
			if (drag) commit(drag.a, drag.b);
			drag = null;
		}}
		onpointerleave={() => (hover = null)}
		ondblclick={() => onRange(null, null)}
		onkeydown={onKeydown}
		onblur={() => {
			hover = null;
			drag = null;
		}}
		role="group"
		aria-label="Runs per day. Drag or use the arrow keys to filter by date."
		aria-keyshortcuts="ArrowLeft ArrowRight Shift+ArrowLeft Shift+ArrowRight Enter"
	>
		{#each days as d, i (d.day)}
			{@const w = worst(d)}
			{@const dim =
				(selected && !inRange(d)) ||
				(drag && (i < Math.min(drag.a, drag.b) || i > Math.max(drag.a, drag.b)))}
			<div class="relative flex h-full min-w-0 flex-1 flex-col justify-end">
				<div
					class="w-full rounded-t-[3px] transition-colors {d.runs ? '' : 'h-px'} {hover === i
						? 'bg-foreground'
						: 'bg-series'} {dim ? 'opacity-25' : ''}"
					style={d.runs ? `height: ${Math.max((d.runs / max) * 100, 6)}%` : ''}
				></div>
				<span
					class="mt-[3px] h-[3px] w-full rounded-full {w
						? SEVERITY_CHIP[w].edge
						: 'bg-transparent'} {dim ? 'opacity-25' : ''}"
				></span>
			</div>
		{/each}
		{#if tip}
			<div
				class="pointer-events-none absolute top-full z-30 mt-5 rounded-md border bg-popover px-2 py-1 text-2xs whitespace-nowrap text-popover-foreground shadow-md {hover! >
				days.length * 0.66
					? '-translate-x-full'
					: hover! < days.length * 0.33
						? ''
						: '-translate-x-1/2'}"
				style="left: {((hover! + 0.5) / days.length) * 100}%"
			>
				<div class="font-medium">{formatShortDate(tip.day, true)}</div>
				<div class="font-mono text-muted-foreground">
					{plural(tip.runs, 'run')}{tip.failed ? ` · ${tip.failed} failed` : ''}
					{#each historyPrefs.severities as s (s)}
						{#if tip[s as 'critical']}<span class={SEVERITY_CHIP[s].ink}>
								· {tip[s as 'critical']} with {s} findings</span
							>{/if}
					{/each}
				</div>
			</div>
		{/if}
	</div>
	<span class="sr-only" aria-live="polite">
		{tip ? `${formatShortDate(tip.day, true)}, ${plural(tip.runs, 'run')}` : ''}
	</span>
	<div class="flex justify-between font-mono text-2xs text-muted-foreground">
		<span>{days.length ? formatShortDate(days[0].day, true) : ''}</span>
		<span>max {plural(max, 'run')} a day</span>
		<span>Today</span>
	</div>
</div>
