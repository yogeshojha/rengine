<script lang="ts">
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import Check from '@lucide/svelte/icons/check';
	import Download from '@lucide/svelte/icons/download';
	import { SCAN_SORT_KEYS, type ScanSortKey, type ScanSortDir } from '$lib/types/scan';
	import type { ExportFormat } from '$lib/utilities/scan-export';

	interface Props {
		sortKey: ScanSortKey;
		sortDir: ScanSortDir;
		onSort: (key: ScanSortKey) => void;
		onExport: (format: ExportFormat) => void;
		exportDisabled?: boolean;
	}

	let { sortKey, sortDir, onSort, onExport, exportDisabled = false }: Props = $props();

	const SORT_LABELS: Record<ScanSortKey, string> = {
		started: 'Started',
		duration: 'Duration',
		status: 'Status',
		subdomains: SURFACE[SurfaceDimension.WEB_ASSETS].label,
		vulnerabilities: 'Vulnerabilities'
	};

	let activeLabel = $derived(SORT_LABELS[sortKey] ?? 'Sort');
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
			{#each SCAN_SORT_KEYS as key (key)}
				<DropdownMenu.Item
					onSelect={(e) => {
						e.preventDefault();
						onSort(key);
					}}
					class="gap-2"
				>
					<span class="w-4">
						{#if sortKey === key}
							<Check class="h-4 w-4" />
						{/if}
					</span>
					<span class="flex-1">{SORT_LABELS[key]}</span>
					{#if sortKey === key}
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
