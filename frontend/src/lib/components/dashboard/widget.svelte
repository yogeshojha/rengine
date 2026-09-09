<script lang="ts">
	import type { Snippet } from 'svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PanelHead from '$lib/components/panel-head.svelte';

	interface Props {
		title: string;
		description?: string;
		href?: string;
		hrefLabel?: string;
		loading?: boolean;
		class?: string;
		bodyClass?: string;
		head?: Snippet;
		children: Snippet;
		footer?: Snippet;
	}

	let {
		title,
		description,
		href,
		hrefLabel = 'Open',
		loading = false,
		class: className = '',
		bodyClass = '',
		head,
		children,
		footer
	}: Props = $props();
</script>

<Card.Root class="flex flex-col gap-0 overflow-hidden py-0 {className}">
	<PanelHead {title} {description}>
		{#if head}{@render head()}{/if}
		{#if href}
			<a
				{href}
				class="flex items-center gap-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				{hrefLabel}
				<ArrowUpRight class="size-3" />
			</a>
		{/if}
	</PanelHead>
	{#if loading}
		<div class="flex flex-col gap-3 px-5 py-4">
			<Skeleton class="h-5 w-2/3" />
			<Skeleton class="h-24 w-full" />
			<Skeleton class="h-5 w-1/2" />
		</div>
	{:else}
		<div class="flex min-h-0 flex-1 flex-col {bodyClass}">
			{@render children()}
		</div>
	{/if}
	{#if footer && !loading}
		<div class="mt-auto border-t px-5 py-2.5 text-xs text-muted-foreground">
			{@render footer()}
		</div>
	{/if}
</Card.Root>
