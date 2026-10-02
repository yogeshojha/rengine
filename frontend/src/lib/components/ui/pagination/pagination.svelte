<script lang="ts">
	import { Pagination as PaginationPrimitive } from 'bits-ui';

	import { cn } from '$lib/utils.js';
	import { IsMobile } from '$lib/hooks/is-mobile.svelte.js';

	let {
		ref = $bindable(null),
		class: className,
		count = 0,
		perPage = 20,
		page = $bindable(1),
		siblingCount,
		...restProps
	}: PaginationPrimitive.RootProps = $props();

	const narrow = new IsMobile(640);
</script>

<PaginationPrimitive.Root
	bind:ref
	bind:page
	role="navigation"
	aria-label="pagination"
	data-slot="pagination"
	class={cn('mx-auto flex w-full justify-center', className)}
	{count}
	{perPage}
	siblingCount={siblingCount ?? (narrow.current ? 0 : 1)}
	{...restProps}
/>
