<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import { TOOLBOX_ICON } from '$lib/config/toolbox';
	import { IS_MAC } from '$lib/utils';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	function onKeydown(event: KeyboardEvent) {
		if (event.key.toLowerCase() !== 'k' || !(event.metaKey || event.ctrlKey)) return;
		if (!event.shiftKey) return;
		event.preventDefault();
		open = !open;
	}
</script>

<svelte:window onkeydown={onKeydown} />

<Hint text="Toolbox · {IS_MAC ? '⌘⇧K' : 'Ctrl+Shift+K'}">
	{#snippet child(hintProps)}
		<span {...hintProps} class="inline-flex">
			<Button variant="ghost" size="icon" onclick={() => (open = true)}>
				<TOOLBOX_ICON class="h-4 w-4" />
				<span class="sr-only">Toolbox</span>
			</Button>
		</span>
	{/snippet}
</Hint>
