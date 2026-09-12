<script lang="ts">
	import type { PulseBucket } from '$lib/utilities/mcp';

	interface Props {
		buckets: PulseBucket[];
		since?: number | null;
		onHover?: (bucket: PulseBucket | null) => void;
	}

	let { buckets, since = null, onHover }: Props = $props();

	const HOUR = 3_600_000;
	const unknown = (b: PulseBucket) => since !== null && b.start + HOUR <= since;

	const H = 44;
	const GAP = 3;
	const max = $derived(Math.max(1, ...buckets.map((b) => b.calls)));
	const hourLabel = (ms: number) =>
		new Date(ms).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
	const ticks = $derived(
		buckets.filter((_, i) => i % 6 === 0 || i === buckets.length - 1).map((b) => hourLabel(b.start))
	);

	let hovered = $state<number | null>(null);

	function enter(i: number) {
		hovered = i;
		onHover?.(buckets[i]);
	}
	function leave() {
		hovered = null;
		onHover?.(null);
	}
</script>

<div class="flex flex-col gap-1.5">
	<div
		class="grid h-[{H}px] items-end"
		style="grid-template-columns: repeat({buckets.length}, minmax(0, 1fr)); column-gap: {GAP}px; height: {H}px"
		role="img"
		aria-label="Calls per hour over the last {buckets.length} hours"
		onmouseleave={leave}
	>
		{#each buckets as b, i (b.start)}
			{@const height = b.calls ? Math.max(3, Math.round((b.calls / max) * H)) : 2}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="flex h-full items-end"
				onmouseenter={() => enter(i)}
				onfocus={() => enter(i)}
				onblur={leave}
			>
				{#if unknown(b)}
					<div class="w-full border-t border-dashed border-muted-foreground/30"></div>
				{:else}
					<div
						class="w-full rounded-[2px] transition-[opacity,background-color] duration-150 {b.calls
							? hovered === null || hovered === i
								? 'bg-info'
								: 'bg-info/40'
							: 'bg-muted-foreground/15'}"
						style="height: {height}px"
					></div>
				{/if}
			</div>
		{/each}
	</div>
	<div class="flex justify-between font-mono text-[10px] text-muted-foreground tabular-nums">
		{#each ticks as t, i (i)}
			<span>{t}</span>
		{/each}
	</div>
</div>
