<script lang="ts" module>
	let lastPress = 0;
	let lastMove = 0;
	let lastKey = 0;

	if (typeof window !== 'undefined') {
		window.addEventListener('pointerup', () => (lastPress = performance.now()), true);
		window.addEventListener('keydown', () => (lastKey = performance.now()), true);
		window.addEventListener(
			'pointermove',
			(e) => {
				if (e.movementX || e.movementY) lastMove = performance.now();
			},
			true
		);
	}

	function asked(): boolean {
		return lastMove >= lastPress || lastKey >= lastPress;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Tooltip from '$lib/components/ui/tooltip';

	interface Props {
		text?: string | null;
		side?: 'top' | 'right' | 'bottom' | 'left';
		child: Snippet<[Record<string, unknown>]>;
	}

	let { text, side = 'top', child: element }: Props = $props();

	let open = $state(false);
</script>

{#if text}
	<Tooltip.Root ignoreNonKeyboardFocus bind:open={() => open, (v) => (open = v && asked())}>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				{@render element(props)}
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content {side} class="max-w-xs wrap-anywhere">{text}</Tooltip.Content>
	</Tooltip.Root>
{:else}
	{@render element({})}
{/if}
