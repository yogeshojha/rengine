<script lang="ts" generics="T extends { id: string; label: string; color?: string }">
	import X from '@lucide/svelte/icons/x';
	import { Badge } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';

	interface Props {
		chips: T[];
		onRemove: (chip: T) => void;
		onClear: () => void;
	}

	let { chips, onRemove, onClear }: Props = $props();
</script>

{#if chips.length > 0}
	<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
		{#each chips as chip (chip.id)}
			<Badge variant="outline" class="gap-1 bg-background font-normal">
				{#if chip.color}
					<span class="size-2 rounded-full" style="background-color: {chip.color}"></span>
				{/if}
				{chip.label}
				<Hint text="Remove filter {chip.label}">
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							onclick={() => onRemove(chip)}
							aria-label="Remove filter {chip.label}"
						>
							<X class="h-3 w-3" />
						</button>
					{/snippet}
				</Hint>
			</Badge>
		{/each}
		<button
			type="button"
			class="ml-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			onclick={() => onClear()}
			aria-label="Clear all filters"
		>
			Clear all
		</button>
	</div>
{/if}
