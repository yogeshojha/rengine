<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { cn } from '$lib/utils.js';

	interface Props {
		/** Shows "N new" instead of "New" when only some of a group are new. */
		count?: number | null;
		/** `xs` for table rows and inline meta, `sm` for sheet headers next to other badges. */
		size?: 'xs' | 'sm';
		class?: string;
	}

	let { count = null, size = 'xs', class: className }: Props = $props();
</script>

<Badge variant="info" class={cn(size === 'xs' ? 'h-4 px-1 text-2xs' : 'font-normal', className)}
	>{count != null ? `${count.toLocaleString()} new` : 'New'}</Badge
>
