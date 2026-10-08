<script lang="ts">
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import { cn } from '$lib/utils';

	interface Props {
		href: string;
		label: string;
		class?: string;
	}

	let { href, label, class: className }: Props = $props();
</script>

<a
	{href}
	class={cn(
		'inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground',
		className
	)}
>
	<ArrowLeft class="size-3.5" />
	{label}
</a>
