<script lang="ts">
	import { cn } from '$lib/utils';
	import type { DimensionDelta } from '$lib/types/compare';

	interface Props {
		delta: DimensionDelta;
		class?: string;
	}

	let { delta, class: className }: Props = $props();

	const SEGMENTS = [
		{ key: 'appeared', fill: 'bg-primary' },
		{ key: 'changed', fill: 'bg-info' },
		{ key: 'disappeared', fill: 'bg-muted-foreground/45' },
		{ key: 'unconfirmed', fill: 'bg-warning/50' },
		{ key: 'unchanged', fill: 'bg-border' }
	] as const;

	let total = $derived(
		delta.appeared + delta.changed + delta.disappeared + delta.unconfirmed + delta.unchanged
	);
	let parts = $derived(SEGMENTS.map((s) => ({ ...s, n: delta[s.key] })).filter((s) => s.n > 0));
</script>

<div class={cn('flex h-1 w-full gap-px overflow-hidden rounded-full', className)}>
	{#if total === 0}
		<span class="h-full flex-1 rounded-full bg-border/60"></span>
	{:else}
		{#each parts as part (part.key)}
			<span
				class="h-full rounded-full {part.fill}"
				style="flex: {Math.max(part.n / total, 0.012)} 1 0"
			></span>
		{/each}
	{/if}
</div>
