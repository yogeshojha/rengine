<script lang="ts">
	import { formatMonthYear } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { REPORT_STAGE_FILL, REPORT_STAGE_ORDER, formatMoney } from '$lib/config/bounty-reports';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import type { MonthPoint } from '$lib/types/bounty-report';

	interface Props {
		months: MonthPoint[];
		currency: string | null;
		from: string | null;
		to: string | null;
		onRange: (from: string | null, to: string | null) => void;
	}

	let { months, currency, from, to, onRange }: Props = $props();

	const total = (m: MonthPoint) => m.open + m.resolved + m.closed;
	let max = $derived(Math.max(1, ...months.map(total)));
	let hover = $state<number | null>(null);
	let drag = $state<{ a: number; b: number } | null>(null);
	let el = $state<HTMLDivElement | null>(null);

	let fromT = $derived(from ? new Date(from).getTime() : null);
	let toT = $derived(to ? new Date(to).getTime() : null);
	const start = (m: MonthPoint) => new Date(`${m.month}T00:00:00Z`).getTime();
	const inRange = (m: MonthPoint) =>
		fromT != null && start(m) >= fromT - 1 && (toT == null || start(m) < toT);
	let selected = $derived(fromT != null);

	function next(month: string): string {
		const [y, m] = month.split('-').map(Number);
		return new Date(Date.UTC(y, m, 1)).toISOString();
	}

	function indexAt(clientX: number): number {
		if (!el) return 0;
		const r = el.getBoundingClientRect();
		return Math.max(
			0,
			Math.min(months.length - 1, Math.floor(((clientX - r.left) / r.width) * months.length))
		);
	}

	function commit(a: number, b: number) {
		if (!months.length) return;
		const lo = Math.min(a, b);
		const hi = Math.max(a, b);
		onRange(new Date(start(months[lo])).toISOString(), next(months[hi].month));
	}

	let tip = $derived(hover != null ? months[hover] : null);
	const monthLabel = (m: string) => formatMonthYear(`${m}T00:00:00Z`, true);
</script>

<div class="flex min-w-0 flex-col gap-1">
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		bind:this={el}
		class="relative flex h-14 cursor-crosshair touch-none items-end gap-[2px] select-none"
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
		onpointercancel={() => {
			drag = null;
			hover = null;
		}}
		onpointerleave={() => (hover = null)}
		ondblclick={() => onRange(null, null)}
		role="group"
		aria-label="Reports submitted per month. Drag to filter by date."
	>
		{#each months as m, i (m.month)}
			{@const n = total(m)}
			{@const dim =
				(selected && !inRange(m)) ||
				(drag && (i < Math.min(drag.a, drag.b) || i > Math.max(drag.a, drag.b)))}
			<div
				class="relative flex h-full min-w-0 flex-1 flex-col justify-end {dim ? 'opacity-25' : ''}"
			>
				{#if n}
					<div
						class="flex w-full flex-col-reverse overflow-hidden rounded-t-[3px] {hover === i
							? 'ring-1 ring-foreground'
							: ''}"
						style="height: {Math.max((n / max) * 100, 6)}%"
					>
						{#each REPORT_STAGE_ORDER as stage (stage)}
							{#if m[stage]}
								<span
									class="w-full"
									style="flex: {m[stage]} 1 0; background: {REPORT_STAGE_FILL[stage]}"
								></span>
							{/if}
						{/each}
					</div>
				{:else}
					<div class="h-px w-full bg-border"></div>
				{/if}
				<span
					class="mt-[3px] h-[3px] w-full rounded-full {m.awards ? 'bg-series' : 'bg-transparent'}"
				></span>
			</div>
		{/each}
		{#if tip}
			<div
				class="pointer-events-none absolute top-full z-30 mt-5 rounded-md border bg-popover px-2 py-1 text-2xs whitespace-nowrap text-popover-foreground shadow-md {hover! >
				months.length * 0.66
					? '-translate-x-full'
					: hover! < months.length * 0.33
						? ''
						: '-translate-x-1/2'}"
				style="left: {((hover! + 0.5) / months.length) * 100}%"
			>
				<div class="font-medium">{monthLabel(tip.month)}</div>
				<div class="font-mono text-muted-foreground">
					{total(tip)} submitted
					{#each REPORT_STAGE_ORDER as stage (stage)}
						{#if tip[stage]}
							<span> · {tip[stage]} {bountyVocabulary.stageLabel(stage).toLowerCase()}</span>
						{/if}
					{/each}
				</div>
				{#if tip.awards && currency}
					<div class="font-mono">
						{formatMoney(tip.earned, currency)} · {plural(tip.awards, 'payment')}
					</div>
				{/if}
			</div>
		{/if}
	</div>
	<div
		class="flex flex-wrap justify-between gap-x-3 gap-y-1 font-mono text-2xs text-muted-foreground"
	>
		<span>{months.length ? monthLabel(months[0].month) : ''}</span>
		<span class="flex flex-wrap items-center gap-x-3 gap-y-1">
			{#each REPORT_STAGE_ORDER as stage (stage)}
				<span class="flex items-center gap-1">
					<span class="size-1.5 rounded-full" style="background: {REPORT_STAGE_FILL[stage]}"></span>
					{bountyVocabulary.stageLabel(stage)}
				</span>
			{/each}
			<span class="flex items-center gap-1">
				<span class="h-[3px] w-2 rounded-full bg-series"></span>
				Paid
			</span>
		</span>
		<span>{months.length ? monthLabel(months[months.length - 1].month) : ''}</span>
	</div>
</div>
