<script lang="ts">
	import { cn } from '$lib/utils';

	let { class: className = '' }: { class?: string } = $props();
</script>

<svg viewBox="0 0 32 32" class={cn('size-6 shrink-0', className)} aria-hidden="true">
	<rect width="32" height="32" rx="7" fill="var(--primary)" />
	<path
		d="M12.5 23.5V11.5M12.5 17.5c0-3.6 2.4-6 6-6h1.5"
		fill="none"
		stroke="var(--primary-foreground)"
		stroke-width="3.4"
		stroke-linecap="round"
		stroke-linejoin="round"
	/>
</svg>
