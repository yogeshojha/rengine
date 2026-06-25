<script lang="ts">
	import Building2 from '@lucide/svelte/icons/building-2';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Tag from '@lucide/svelte/icons/tag';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import X from '@lucide/svelte/icons/x';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';

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

<div
	class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 max-w-[calc(100vw-1rem)] transition-all duration-300 ease-out {selectedCount >
	0
		? 'translate-y-0 opacity-100'
		: 'translate-y-3 opacity-0 pointer-events-none'}"
>
	<div
		class="flex flex-wrap items-center justify-center gap-0.5 gap-y-1 bg-popover text-popover-foreground backdrop-blur-xl backdrop-saturate-180 border border-border rounded-2xl shadow-xl shadow-black/30 p-1.5"
	>
		<div class="flex items-center px-2.5 py-1.5">
			<span class="text-xs font-medium text-muted-foreground tabular-nums">
				{selectedCount}
				{selectedCount === 1 ? 'target' : 'targets'} selected
			</span>
		</div>

		<Separator orientation="vertical" class="h-4 self-center mx-0.5" />

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
			<DropdownMenu.Content align="center" class="max-h-72 w-48 overflow-y-auto">
				{#if tags.length === 0}
					<DropdownMenu.Item disabled>No tags</DropdownMenu.Item>
				{:else}
					{#each tags as tag (tag.id)}
						<DropdownMenu.Item onclick={() => onAddTag(tag.name)} class="gap-2">
							<span class="h-2.5 w-2.5 rounded-full shrink-0" style="background-color: {tag.color}"
							></span>
							<span class="truncate">{tag.name}</span>
						</DropdownMenu.Item>
					{/each}
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
			<DropdownMenu.Content align="center" class="max-h-72 w-48 overflow-y-auto">
				{#if organizations.length === 0}
					<DropdownMenu.Item disabled>No organizations</DropdownMenu.Item>
				{:else}
					{#each organizations as org (org.id)}
						<DropdownMenu.Item onclick={() => onAddOrg(org.name)} class="truncate">
							{org.name}
						</DropdownMenu.Item>
					{/each}
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

		<Separator orientation="vertical" class="h-4 self-center mx-0.5" />
		<Button variant="ghost" size="icon-sm" class="text-muted-foreground" onclick={onClear}>
			<X class="h-3.5 w-3.5" />
		</Button>
	</div>
</div>
