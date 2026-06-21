<script lang="ts">
	import { PinInput } from 'bits-ui';
	import { cn } from '$lib/utils.js';

	interface Props {
		value: string;
		onValueChange: (v: string) => void;
		length?: number;
		disabled?: boolean;
	}

	let { value, onValueChange, length = 6, disabled = false }: Props = $props();
</script>

<PinInput.Root
	{value}
	{disabled}
	maxlength={length}
	inputmode="numeric"
	onValueChange={(v) => onValueChange(v.replace(/\D/g, '').slice(0, length))}
	class="flex w-full items-center gap-1.5 sm:gap-2"
>
	{#snippet children({ cells })}
		{#each cells as cell, i (i)}
			<PinInput.Cell
				{cell}
				class={cn(
					'relative flex aspect-square h-12 w-full max-w-12 min-w-0 flex-1 items-center justify-center rounded-md border border-input bg-background text-lg font-medium tabular-nums shadow-xs transition-[color,box-shadow] outline-none dark:bg-input/30',
					cell.isActive && 'border-ring ring-ring/50 z-10 ring-[3px]',
					disabled && 'cursor-not-allowed opacity-50'
				)}
			>
				{#if cell.char}{cell.char}{/if}
				{#if cell.hasFakeCaret}
					<div class="pointer-events-none absolute inset-0 flex items-center justify-center">
						<div class="h-5 w-px animate-caret-blink bg-foreground"></div>
					</div>
				{/if}
			</PinInput.Cell>
		{/each}
	{/snippet}
</PinInput.Root>
