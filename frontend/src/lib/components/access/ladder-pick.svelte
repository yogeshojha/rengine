<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { MCP_CAPABILITIES, MCP_CAPABILITY_LABELS, TOUCHES_TARGETS } from '$lib/types/mcp';

	interface Props {
		level: number;
		allowed: Set<string>;
		onChange: (level: number) => void;
		blockedHint?: string;
	}

	let { level, allowed, onChange, blockedHint = 'Off in the ceiling' }: Props = $props();
</script>

<div
	role="radiogroup"
	aria-label="Capabilities"
	class="inline-flex h-8 w-fit overflow-hidden rounded-md border bg-background"
>
	{#each MCP_CAPABILITIES as cap, i (cap)}
		{@const blocked = !allowed.has(cap)}
		{@const inside = i <= level && !blocked}
		<Hint text={blocked ? blockedHint : ''}>
			{#snippet child(props)}
				<span {...props} class="inline-flex border-r last:border-r-0">
					<button
						type="button"
						role="radio"
						aria-checked={i === level}
						disabled={blocked}
						class="px-3 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40 {inside
							? TOUCHES_TARGETS.includes(cap)
								? 'bg-warning/10 font-medium text-warning'
								: 'bg-muted font-medium text-foreground'
							: 'text-muted-foreground hover:text-foreground'}"
						onclick={() => onChange(i)}
					>
						{MCP_CAPABILITY_LABELS[cap]}
					</button>
				</span>
			{/snippet}
		</Hint>
	{/each}
</div>
