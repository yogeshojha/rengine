<script lang="ts">
	import { MCP_CAPABILITIES, MCP_CAPABILITY_LABELS, TOUCHES_TARGETS } from '$lib/types/mcp';
	import { cn } from '$lib/utils';

	interface Props {
		granted: string[];
		ladder?: boolean;
		class?: string;
	}

	let { granted, ladder = false, class: className }: Props = $props();

	const shown = $derived(
		ladder ? [...MCP_CAPABILITIES] : MCP_CAPABILITIES.filter((c) => granted.includes(c))
	);
</script>

<span class={cn('inline-flex flex-wrap items-center gap-1', className)}>
	{#each shown as cap (cap)}
		{@const on = granted.includes(cap)}
		{@const warn = TOUCHES_TARGETS.includes(cap)}
		<span
			class="inline-flex h-5 items-center rounded border px-1.5 text-2xs leading-none font-medium {on
				? warn
					? 'border-warning/40 bg-warning/10 text-warning'
					: 'border-border bg-muted/60 text-foreground'
				: 'border-dashed border-border/70 text-muted-foreground/45'}"
		>
			{MCP_CAPABILITY_LABELS[cap]}
		</span>
	{/each}
</span>
