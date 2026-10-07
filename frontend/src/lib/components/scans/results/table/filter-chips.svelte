<script lang="ts" generics="T extends { id: string; label: string; color?: string }">
	import X from '@lucide/svelte/icons/x';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
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
			<Badge
				variant="outline"
				class="max-w-full min-w-0 gap-1 overflow-visible bg-background pr-0.5 font-normal"
			>
				{#if chip.color}
					<span
						class="size-2 shrink-0 rounded-full"
						style="background-color: {chip.color}"
						aria-hidden="true"
					></span>
				{/if}
				<span class="min-w-0 truncate" title={chip.label}>{chip.label}</span>
				<Hint text="Remove filter {chip.label}">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon-xs"
							class="size-4 shrink-0 rounded-full text-muted-foreground hover:text-foreground"
							onclick={() => onRemove(chip)}
							aria-label="Remove filter {chip.label}"
						>
							<X class="size-3" />
						</Button>
					{/snippet}
				</Hint>
			</Badge>
		{/each}
		<Button
			variant="ghost"
			size="xs"
			class="text-muted-foreground"
			onclick={() => onClear()}
			aria-label="Clear all filters"
		>
			Clear all
		</Button>
	</div>
{/if}
