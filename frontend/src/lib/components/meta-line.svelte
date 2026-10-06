<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	interface Props {
		class?: string;
		children: Snippet;
	}

	let { class: className, children }: Props = $props();
</script>

<!-- a line-start dot falls in the clipped gutter -->
<div class={cn('overflow-hidden', className)}>
	<div
		class="-ms-4 flex flex-wrap items-center gap-y-1 *:relative *:ps-4 *:before:absolute *:before:start-1.5 *:before:top-1/2 *:before:-translate-y-1/2 *:before:leading-none *:before:content-['·']"
	>
		{@render children()}
	</div>
</div>
