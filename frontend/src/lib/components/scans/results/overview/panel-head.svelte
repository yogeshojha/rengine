<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	interface Props {
		title: string;
		description?: string;
		class?: string;
		children?: Snippet;
	}

	let { title, description, class: className, children }: Props = $props();
</script>

<div
	class={cn(
		'flex flex-wrap items-start justify-between gap-x-6 gap-y-1 border-b px-5 py-4',
		className
	)}
>
	<div class="flex min-w-0 flex-col gap-0.5">
		<h2 class="text-base leading-6 font-semibold">{title}</h2>
		{#if description}
			<p class="text-xs text-muted-foreground">{description}</p>
		{/if}
	</div>
	{#if children}
		<div class="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
			{@render children()}
		</div>
	{/if}
</div>
