<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { IconComponent } from '$lib/config/icons';
	import * as Empty from '$lib/components/ui/empty';
	import { cn } from '$lib/utils.js';

	interface Props {
		icon?: IconComponent;
		title: string;
		description?: string;
		class?: string;
		compact?: boolean;
		children?: Snippet;
	}

	let {
		icon: Icon,
		title,
		description,
		class: className,
		compact = false,
		children
	}: Props = $props();
</script>

<Empty.Root class={cn('border bg-muted/20', compact ? 'py-8' : 'py-20', className)}>
	<Empty.Header>
		{#if Icon}
			<Empty.Media class={cn('rounded-2xl bg-muted', compact ? 'size-12' : 'size-16')}>
				<Icon size={compact ? 20 : 28} class="text-muted-foreground" />
			</Empty.Media>
		{/if}
		<Empty.Title class={compact ? '' : 'text-lg font-bold'}>{title}</Empty.Title>
		{#if description}
			<Empty.Description class="max-w-md">{description}</Empty.Description>
		{/if}
	</Empty.Header>
	{#if children}
		<Empty.Content>{@render children()}</Empty.Content>
	{/if}
</Empty.Root>
