<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	interface Props {
		title: string;
		/** One line under the title. A snippet for inline links or buttons. */
		description?: string | Snippet;
		/** Buttons on the right. */
		actions?: Snippet;
		/** Inline after the title (copy button, badges). */
		titleAside?: Snippet;
		/** Extra rows under the description (meta lines, long text). */
		children?: Snippet;
		/** Mono title, for IDs. */
		mono?: boolean;
		class?: string;
	}

	let {
		title,
		description,
		actions,
		titleAside,
		children,
		mono = false,
		class: className
	}: Props = $props();

	const align = $derived(children ? 'items-start' : description ? 'items-end' : 'items-center');
</script>

<div class={cn('flex flex-wrap justify-between gap-3', align, className)}>
	<div class="flex min-w-0 flex-col">
		{#if titleAside}
			<div class="flex flex-wrap items-center gap-2">
				<h1 class={cn('text-2xl font-semibold tracking-tight', mono && 'font-mono')}>{title}</h1>
				{@render titleAside()}
			</div>
		{:else}
			<h1 class={cn('text-2xl font-semibold tracking-tight', mono && 'font-mono')}>{title}</h1>
		{/if}
		{#if typeof description === 'string'}
			<p class="mt-1 text-sm text-muted-foreground">{description}</p>
		{:else if description}
			<p class="mt-1 text-sm text-muted-foreground">{@render description()}</p>
		{/if}
		{#if children}
			<div class="mt-2 flex min-w-0 flex-col gap-2">{@render children()}</div>
		{/if}
	</div>
	{#if actions}
		<div class="flex flex-wrap items-center gap-2">{@render actions()}</div>
	{/if}
</div>
