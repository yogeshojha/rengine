<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Card from '$lib/components/ui/card';
	import { cn } from '$lib/utils';

	interface Props {
		title: string;
		description?: string;
		class?: string;
		children: Snippet;
		footer?: Snippet;
	}

	let { title, description, class: className, children, footer }: Props = $props();
</script>

<Card.Root class={cn('flex flex-col gap-4 py-5', className)}>
	<Card.Header class="gap-1">
		<Card.Title>{title}</Card.Title>
		{#if description}
			<Card.Description>{description}</Card.Description>
		{/if}
	</Card.Header>
	<Card.Content class="flex-1">
		{@render children()}
	</Card.Content>
	{#if footer}
		<Card.Footer class="flex-col items-start gap-1.5 text-sm">
			{@render footer()}
		</Card.Footer>
	{/if}
</Card.Root>
