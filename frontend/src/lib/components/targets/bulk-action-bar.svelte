<script lang="ts">
	import Building2 from '@lucide/svelte/icons/building-2';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Tag from '@lucide/svelte/icons/tag';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import SelectionActionBar from '@/components/selection-action-bar.svelte';

	interface Props {
		selectedCount: number;
		tags: { id: string; name: string; color: string }[];
		organizations: { id: string; name: string }[];
		onScan: () => void;
		onDelete: () => void;
		onClear: () => void;
		onEnrich: (kind: 'whois' | 'dns' | 'bgp') => void;
		onAddTag: (name: string) => void;
		onAddOrg: (name: string) => void;
	}

	let {
		selectedCount,
		tags,
		organizations,
		onScan,
		onDelete,
		onClear,
		onEnrich,
		onAddTag,
		onAddOrg
	}: Props = $props();
</script>

<SelectionActionBar {selectedCount} noun="target" {onClear}>
	<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={onScan}>
		<Play class="h-3.5 w-3.5 text-muted-foreground" />
		Scan
	</Button>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="sm" class="gap-2 font-medium">
					<RefreshCw class="h-3.5 w-3.5 text-muted-foreground" />
					Enrich
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="center" class="w-40">
			<DropdownMenu.Item onclick={() => onEnrich('whois')}>Re-run WHOIS</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => onEnrich('dns')}>Re-run DNS</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => onEnrich('bgp')}>Re-run BGP</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="sm" class="gap-2 font-medium">
					<Tag class="h-3.5 w-3.5 text-muted-foreground" />
					Tag
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="center" class="max-h-none w-48 overflow-visible">
			{#if tags.length === 0}
				<DropdownMenu.Item disabled>No tags</DropdownMenu.Item>
			{:else}
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
					{#each tags as tag (tag.id)}
						<DropdownMenu.Item onclick={() => onAddTag(tag.name)} class="gap-2">
							<span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background-color: {tag.color}"
							></span>
							<span class="truncate">{tag.name}</span>
						</DropdownMenu.Item>
					{/each}
				</ScrollArea>
			{/if}
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="sm" class="gap-2 font-medium">
					<Building2 class="h-3.5 w-3.5 text-muted-foreground" />
					Org
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="center" class="max-h-none w-48 overflow-visible">
			{#if organizations.length === 0}
				<DropdownMenu.Item disabled>No organizations</DropdownMenu.Item>
			{:else}
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
					{#each organizations as org (org.id)}
						<DropdownMenu.Item onclick={() => onAddOrg(org.name)} class="truncate">
							{org.name}
						</DropdownMenu.Item>
					{/each}
				</ScrollArea>
			{/if}
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<Button
		variant="ghost"
		size="sm"
		class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
		onclick={onDelete}
	>
		<Trash2 class="h-3.5 w-3.5" />
		Delete
	</Button>
</SelectionActionBar>
