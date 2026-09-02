<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import { cn } from '$lib/utils';
	import { FOOTPRINT_HELP, FOOTPRINT_LABEL, type Footprint } from '$lib/utilities/engine-summary';

	interface Props {
		footprint: Footprint;
		requestsPerSecond?: number;
		class?: string;
	}

	let { footprint, requestsPerSecond = 0, class: className }: Props = $props();

	const LEVEL: Record<Footprint, number> = { none: 0, quiet: 1, moderate: 2, loud: 3 };
	const level = $derived(LEVEL[footprint]);
</script>

<Tooltip.Root>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<span
				{...props}
				class={cn(
					'inline-flex items-center gap-1.5 text-xs whitespace-nowrap',
					footprint === 'loud' ? 'text-warning' : 'text-muted-foreground',
					className
				)}
			>
				{#if footprint === 'none'}
					<EyeOff size={12} class="shrink-0" />
				{:else}
					<span class="flex items-end gap-px" aria-hidden="true">
						{#each [1, 2, 3] as bar (bar)}
							<span
								class={cn(
									'w-[3px] rounded-[1px]',
									bar === 1 ? 'h-1.5' : bar === 2 ? 'h-2.5' : 'h-3.5',
									bar <= level
										? footprint === 'loud'
											? 'bg-warning'
											: 'bg-foreground/70'
										: 'bg-border'
								)}
							></span>
						{/each}
					</span>
				{/if}
				<span>{FOOTPRINT_LABEL[footprint]}</span>
				{#if footprint !== 'none' && requestsPerSecond > 0}
					<span class="tabular-nums opacity-80">~{requestsPerSecond}/s</span>
				{/if}
			</span>
		{/snippet}
	</Tooltip.Trigger>
	<Tooltip.Content class="max-w-[240px] text-xs">{FOOTPRINT_HELP[footprint]}</Tooltip.Content>
</Tooltip.Root>
