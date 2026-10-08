<script lang="ts">
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import { page } from '$app/state';
	import { previousPage } from '$lib/stores/previous-page.svelte';
	import { cn } from '$lib/utils';

	interface Props {
		/** where the link goes when the page was opened directly, with no page before it */
		href: string;
		label: string;
		class?: string;
	}

	let { href, label, class: className }: Props = $props();

	let previous = $derived(previousPage.of(page.url.pathname));
</script>

<a
	href={previous?.href ?? href}
	class={cn(
		'inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground',
		className
	)}
>
	<ArrowLeft class="size-3.5" />
	{previous?.label ?? label}
</a>
