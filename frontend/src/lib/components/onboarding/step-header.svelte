<script lang="ts">
	import type { Component } from 'svelte';

	let {
		icon,
		title,
		description
	}: { icon?: Component; title: string; description?: string } = $props();
</script>

<div class="space-y-3">
	{#if icon}
		{@const Icon = icon}
		<div class="flex size-9 items-center justify-center rounded-lg border bg-muted text-foreground">
			<Icon class="size-[18px]" />
		</div>
	{/if}
	<div class="space-y-1.5">
		<h2 class="text-xl font-semibold tracking-tight text-foreground">{title}</h2>
		{#if description}
			<p class="text-sm leading-relaxed text-muted-foreground">{description}</p>
		{/if}
	</div>
</div>
