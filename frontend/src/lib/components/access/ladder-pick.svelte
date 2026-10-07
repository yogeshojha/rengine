<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { cn } from '$lib/utils';
	import { MCP_CAPABILITIES, MCP_CAPABILITY_LABELS, TOUCHES_TARGETS } from '$lib/types/mcp';

	interface Props {
		level: number;
		allowed: Set<string>;
		onChange: (level: number) => void;
	}

	let { level, allowed, onChange }: Props = $props();
</script>

<ToggleGroup.Root
	type="single"
	size="sm"
	spacing={1}
	value={String(level)}
	onValueChange={(v) => v && onChange(Number(v))}
	aria-label="Capabilities"
	class="h-8 gap-0 overflow-hidden rounded-md border bg-background"
>
	{#each MCP_CAPABILITIES as cap, i (cap)}
		{@const blocked = !allowed.has(cap)}
		{@const inside = i <= level && !blocked}
		<Hint text={blocked ? 'Off in the ceiling' : ''}>
			{#snippet child(props)}
				<span {...props} class="inline-flex h-full border-r last:border-r-0">
					<ToggleGroup.Item
						value={String(i)}
						disabled={blocked}
						class={cn(
							'h-full rounded-none px-3 text-xs font-normal disabled:cursor-not-allowed disabled:opacity-40 data-[state=on]:bg-transparent',
							inside
								? TOUCHES_TARGETS.includes(cap)
									? 'bg-warning/10 font-medium text-warning hover:bg-warning/10 hover:text-warning data-[state=on]:bg-warning/10'
									: 'bg-muted font-medium text-foreground data-[state=on]:bg-muted'
								: 'text-muted-foreground hover:bg-transparent hover:text-foreground'
						)}
					>
						{MCP_CAPABILITY_LABELS[cap]}
					</ToggleGroup.Item>
				</span>
			{/snippet}
		</Hint>
	{/each}
</ToggleGroup.Root>
