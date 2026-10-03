<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { VISUAL_MAX_DISTANCE } from '$lib/config/whats-new';

	interface Props {
		distances: number[];
		min: number;
		onChange: (min: number) => void;
	}

	let { distances, min, onChange }: Props = $props();

	const BUCKETS = 8;
	const width = VISUAL_MAX_DISTANCE / BUCKETS;
	let bars = $derived.by(() => {
		const out = Array<number>(BUCKETS).fill(0);
		for (const d of distances) out[Math.min(BUCKETS - 1, Math.floor(d / width))]++;
		return out;
	});
	let top = $derived(Math.max(1, ...bars));
	let matched = $derived(distances.filter((d) => d >= min).length);
</script>

<div class="flex h-9 items-center gap-2 rounded-md border px-2">
	<span class="flex h-4 items-end gap-px" aria-hidden="true">
		{#each bars as n, i (i)}
			{@const lo = i * width}
			<Hint text="{lo} to {lo + width - 1}: {n}">
				{#snippet child(props)}
					<span
						{...props}
						class="w-1.5 rounded-[1px] {lo + width <= min ? 'bg-muted' : ''}"
						style="height: {n ? Math.max(12, (n / top) * 100) : 12}%; {lo + width <= min
							? ''
							: 'background: var(--series)'}"
					></span>
				{/snippet}
			</Hint>
		{/each}
	</span>
	<label class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<span class="tabular-nums">≥ {min}</span>
		<input
			type="range"
			min="1"
			max={VISUAL_MAX_DISTANCE}
			value={min}
			class="h-1 w-20 cursor-pointer accent-primary"
			aria-label="Least distance"
			oninput={(e) => onChange(Number((e.currentTarget as HTMLInputElement).value))}
		/>
		<span class="tabular-nums">{matched}</span>
	</label>
</div>
