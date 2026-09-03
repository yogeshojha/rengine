<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import Check from '@lucide/svelte/icons/check';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import type { SortOption } from './columns';

	interface Props {
		sorts: SortOption[];
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
	}

	let { sorts, sortKey, sortDir, onSort }: Props = $props();

	let activeLabel = $derived(sorts.find((s) => s.key === sortKey)?.label ?? 'Sort');
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
				<ArrowUpDown class="h-4 w-4" />
				<span class="hidden sm:inline">{activeLabel}</span>
				{#if sortDir === 1}
					<ArrowUp class="h-3.5 w-3.5 text-muted-foreground" />
				{:else}
					<ArrowDown class="h-3.5 w-3.5 text-muted-foreground" />
				{/if}
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="max-h-none w-44 overflow-visible">
		<DropdownMenu.Label>Sort by</DropdownMenu.Label>
		<DropdownMenu.Separator />
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
			{#each sorts as s (s.key)}
				<DropdownMenu.Item
					onSelect={(e) => {
						e.preventDefault();
						onSort(s.key);
					}}
					class="gap-2"
				>
					<span class="w-4">
						{#if sortKey === s.key}
							<Check class="h-4 w-4" />
						{/if}
					</span>
					<span class="flex-1">{s.label}</span>
					{#if sortKey === s.key}
						{#if sortDir === 1}
							<ArrowUp class="h-3.5 w-3.5 text-muted-foreground" />
						{:else}
							<ArrowDown class="h-3.5 w-3.5 text-muted-foreground" />
						{/if}
					{/if}
				</DropdownMenu.Item>
			{/each}
		</ScrollArea>
	</DropdownMenu.Content>
</DropdownMenu.Root>
