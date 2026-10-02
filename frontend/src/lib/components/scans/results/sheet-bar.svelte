<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		start?: Snippet;
		below?: Snippet;
		children?: Snippet;
	}

	let { start, below, children }: Props = $props();
</script>

<div class="shrink-0 border-b bg-muted/20">
	<div class="flex flex-wrap items-center gap-2 px-5 py-2">
		{@render start?.()}
		<div class="ml-auto flex min-w-0 flex-wrap items-center justify-end gap-1">
			{@render children?.()}
		</div>
	</div>
	{@render below?.()}
</div>
