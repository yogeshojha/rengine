<script lang="ts">
	import type { Snippet } from 'svelte';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';

	interface Props {
		noun: string;
		index?: number;
		pageOffset?: number;
		total?: number;
		capped?: boolean;
		onStep?: (dir: -1 | 1) => void;
		children?: Snippet;
	}

	let {
		noun,
		index = 0,
		pageOffset = 0,
		total = 0,
		capped = false,
		onStep,
		children
	}: Props = $props();

	let position = $derived(pageOffset + index + 1);
</script>

<div class="flex items-start gap-3 pr-7">
	<div class="flex min-h-7 min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
		{@render children?.()}
	</div>
	{#if total > 1 && index >= 0}
		<div class="flex h-7 shrink-0 items-center gap-0.5 whitespace-nowrap">
			<span class="mr-1 text-xs text-muted-foreground tabular-nums">
				{position.toLocaleString()} / {total.toLocaleString()}{capped ? '+' : ''}
			</span>
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={position <= 1}
							onclick={() => onStep?.(-1)}
							aria-label="Previous {noun}"
						>
							<ChevronUp class="size-4" />
						</Button>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content class="flex items-center gap-1.5">Previous <Kbd>k</Kbd></Tooltip.Content>
			</Tooltip.Root>
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={position >= total}
							onclick={() => onStep?.(1)}
							aria-label="Next {noun}"
						>
							<ChevronDown class="size-4" />
						</Button>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content class="flex items-center gap-1.5">Next <Kbd>j</Kbd></Tooltip.Content>
			</Tooltip.Root>
		</div>
	{/if}
</div>
