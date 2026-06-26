<script lang="ts">
	import type { HTMLTableAttributes } from 'svelte/elements';
	import { cn, type WithElementRef } from '$lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		containerClass,
		children,
		...restProps
	}: WithElementRef<HTMLTableAttributes> & { containerClass?: string } = $props();
</script>

<div data-slot="table-container" class={cn('relative w-full overflow-x-auto', containerClass)}>
	<table
		bind:this={ref}
		data-slot="table"
		class={cn('w-full caption-bottom text-sm', className)}
		{...restProps}
	>
		{@render children?.()}
	</table>
</div>
