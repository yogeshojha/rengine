<script lang="ts">
	import { Tabs as TabsPrimitive } from 'bits-ui';
	import { cn } from '$lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		// every panel here holds focusable content, so the panel itself is not a tab stop
		tabindex = -1,
		...restProps
	}: TabsPrimitive.ContentProps = $props();
</script>

<TabsPrimitive.Content
	bind:ref
	data-slot="tabs-content"
	class={cn('flex-1 outline-none', className)}
	{tabindex}
	{...restProps}
/>
