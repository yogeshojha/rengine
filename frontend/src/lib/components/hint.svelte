<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Tooltip from '$lib/components/ui/tooltip';

	interface Props {
		text?: string | null;
		side?: 'top' | 'right' | 'bottom' | 'left';
		class?: string;
		child: Snippet<[Record<string, unknown>]>;
	}

	let {
		text,
		side = 'top',
		class: className = 'max-w-xs wrap-anywhere',
		child: element
	}: Props = $props();
</script>

{#if text}
	<Tooltip.Root ignoreNonKeyboardFocus>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				{@render element(props)}
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content {side} class={className}>{text}</Tooltip.Content>
	</Tooltip.Root>
{:else}
	{@render element({})}
{/if}
