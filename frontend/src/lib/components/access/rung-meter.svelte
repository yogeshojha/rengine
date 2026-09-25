<script lang="ts">
	import { MCP_CAPABILITIES, MCP_CAPABILITY_LABELS, TOUCHES_TARGETS } from '$lib/types/mcp';
	import { cn } from '$lib/utils';

	interface Props {
		granted: readonly string[];
		effective?: readonly string[];
		class?: string;
	}

	let { granted, effective = granted, class: className }: Props = $props();
</script>

<span
	class={cn('grid w-10 shrink-0 grid-cols-4 gap-0.5', className)}
	role="img"
	aria-label={effective
		.map((c) => MCP_CAPABILITY_LABELS[c as keyof typeof MCP_CAPABILITY_LABELS])
		.join(', ')}
>
	{#each MCP_CAPABILITIES as cap (cap)}
		{@const on = effective.includes(cap)}
		{@const held = !on && granted.includes(cap)}
		<span
			class="h-1.5 rounded-xs {on
				? TOUCHES_TARGETS.includes(cap)
					? 'bg-warning'
					: 'bg-foreground/75'
				: held
					? 'bg-[repeating-linear-gradient(135deg,currentColor_0_2px,transparent_2px_5px)] text-muted-foreground/60'
					: 'bg-muted-foreground/20'}"
		></span>
	{/each}
</span>
