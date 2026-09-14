<script lang="ts">
	import type { Snippet } from 'svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import X from '@lucide/svelte/icons/x';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';

	interface Props {
		id: string;
		title: string;
		description?: string;
		href?: string;
		hrefLabel?: string;
		loading?: boolean;
		class?: string;
		bodyClass?: string;
		tools?: Snippet;
		children: Snippet;
		footer?: Snippet;
	}

	let {
		id,
		title,
		description,
		href,
		hrefLabel = 'Open',
		loading = false,
		class: className = '',
		bodyClass = '',
		tools,
		children,
		footer
	}: Props = $props();
</script>

<section
	class="group/cell -mr-px -mb-px flex min-w-0 flex-col border-r border-b bg-card {className}"
	data-widget={id}
>
	<div class="flex items-start justify-between gap-3 px-4 pt-3.5">
		<div class="flex min-w-0 flex-col gap-0.5">
			<h3 class="text-sm leading-5 font-semibold">{title}</h3>
			{#if description}
				<p class="text-xs text-muted-foreground">{description}</p>
			{/if}
		</div>
		<div class="flex shrink-0 items-center gap-2">
			{#if tools}{@render tools()}{/if}
			{#if href}
				<a
					{href}
					class="flex items-center gap-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					{hrefLabel}
					<ArrowUpRight class="size-3" />
				</a>
			{/if}
			<Hint text="Hide">
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						class="flex size-5 items-center justify-center rounded-sm text-muted-foreground opacity-0 transition-opacity group-hover/cell:opacity-100 hover:bg-muted hover:text-foreground focus-visible:opacity-100"
						aria-label="Hide {title}"
						onclick={() => dashboardLayout.hide(id)}
					>
						<X class="size-3.5" />
					</button>
				{/snippet}
			</Hint>
		</div>
	</div>
	{#if loading}
		<div class="flex flex-col gap-3 px-4 py-4">
			<Skeleton class="h-5 w-2/3" />
			<Skeleton class="h-24 w-full" />
			<Skeleton class="h-5 w-1/2" />
		</div>
	{:else}
		<div class="flex min-h-0 flex-1 flex-col gap-3 px-4 pt-3 pb-4 {bodyClass}">
			{@render children()}
		</div>
	{/if}
	{#if footer && !loading}
		<div
			class="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t px-4 py-2 text-xs text-muted-foreground"
		>
			{@render footer()}
		</div>
	{/if}
</section>
