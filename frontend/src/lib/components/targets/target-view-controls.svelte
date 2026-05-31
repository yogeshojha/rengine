<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ArrowDown, ArrowUp, ArrowUpDown, Check, Download } from 'lucide-svelte';
	import type { SortDir, SortKey } from '$lib/utilities/target-signals';
	import type { ExportFormat } from '$lib/utilities/target-export';

	interface Props {
		sortKey: SortKey;
		sortDir: SortDir;
		onSort: (key: SortKey) => void;
		onExport: (format: ExportFormat) => void;
		exportDisabled?: boolean;
	}

	let { sortKey, sortDir, onSort, onExport, exportDisabled = false }: Props = $props();

	const SORT_OPTIONS: { key: SortKey; label: string }[] = [
		{ key: 'updated', label: 'Last updated' },
		{ key: 'name', label: 'Name' },
		{ key: 'type', label: 'Type' },
		{ key: 'expiry', label: 'Expiry' },
		{ key: 'enrichment', label: 'Enrichment' }
	];

	let activeLabel = $derived(SORT_OPTIONS.find((o) => o.key === sortKey)?.label ?? 'Sort');
</script>

<div class="flex items-center gap-2">
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
					<ArrowUpDown class="h-4 w-4" />
					<span class="hidden sm:inline">{activeLabel}</span>
					{#if sortDir === 'asc'}
						<ArrowUp class="h-3.5 w-3.5 text-muted-foreground" />
					{:else}
						<ArrowDown class="h-3.5 w-3.5 text-muted-foreground" />
					{/if}
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-44">
			<DropdownMenu.Label>Sort by</DropdownMenu.Label>
			<DropdownMenu.Separator />
			{#each SORT_OPTIONS as option (option.key)}
				<DropdownMenu.Item
					onSelect={(e) => {
						e.preventDefault();
						onSort(option.key);
					}}
					class="gap-2"
				>
					<span class="w-4">
						{#if sortKey === option.key}
							<Check class="h-4 w-4" />
						{/if}
					</span>
					<span class="flex-1">{option.label}</span>
					{#if sortKey === option.key}
						{#if sortDir === 'asc'}
							<ArrowUp class="h-3.5 w-3.5 text-muted-foreground" />
						{:else}
							<ArrowDown class="h-3.5 w-3.5 text-muted-foreground" />
						{/if}
					{/if}
				</DropdownMenu.Item>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="outline" size="sm" class="h-9 gap-2" disabled={exportDisabled}>
					<Download class="h-4 w-4" />
					<span class="hidden sm:inline">Export</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-40">
			<DropdownMenu.Label>Export view</DropdownMenu.Label>
			<DropdownMenu.Separator />
			<DropdownMenu.Item onclick={() => onExport('csv')}>CSV</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => onExport('json')}>JSON</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</div>
