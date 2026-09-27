<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	interface Props {
		label: string;
		help?: string;
		for?: string;
		class?: string;
		children: Snippet;
	}

	let { label, help, for: target, class: className, children }: Props = $props();
</script>

<div
	class={cn(
		'grid grid-cols-1 gap-2 border-t border-border/60 px-5 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6',
		className
	)}
>
	<div class="flex min-w-0 flex-col gap-0.5">
		{#if target}
			<label for={target} class="text-sm leading-5 font-medium">{label}</label>
		{:else}
			<span class="text-sm leading-5 font-medium">{label}</span>
		{/if}
		{#if help}
			<span class="text-xs text-muted-foreground">{help}</span>
		{/if}
	</div>
	<div class="flex shrink-0 items-center gap-2">
		{@render children()}
	</div>
</div>
