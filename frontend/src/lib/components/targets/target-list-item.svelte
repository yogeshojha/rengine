<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { formatDistanceToNow } from '$lib/utilities/dates';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '$lib/components/ui/copy-button.svelte';
	import { Building2, Ellipsis, Eye, Pencil, Trash2 } from 'lucide-svelte';

	interface Props {
		target: Target;
		onView: (target: Target) => void;
		onEdit: (target: Target) => void;
		onDelete: (target: Target) => void;
	}

	let { target, onView, onEdit, onDelete }: Props = $props();
</script>

<div
	class="group flex items-center gap-4 px-4 py-3 border-b border-border/50 hover:bg-muted/30 transition-colors"
>
	<!-- Main Content -->
	<div class="w-[280px] min-w-0 space-y-1">
		<!-- Target Value Row -->
		<div class="flex items-center gap-2">
			<span class="font-mono text-sm font-medium truncate">{target.target_value}</span>
			<CopyButton value={target.target_value} class="opacity-0 group-hover:opacity-100 transition-opacity" />
		</div>

		<!-- Display Name -->
		{#if target.display_name}
			<p class="text-sm text-muted-foreground truncate">{target.display_name}</p>
		{/if}
	</div>

	<!-- Organizations -->
	<div class="hidden md:flex items-center gap-1.5 flex-1 min-w-[180px]">
		{#if target.organizations.length > 0}
			{#each target.organizations.slice(0, 2) as org}
				<Badge variant="outline" class="text-xs font-normal gap-1 max-w-[100px]">
					<Building2 class="h-3 w-3 shrink-0" />
					<span class="truncate">{org.name}</span>
				</Badge>
			{/each}
			{#if target.organizations.length > 2}
				<Badge variant="outline" class="text-xs font-normal">
					+{target.organizations.length - 2}
				</Badge>
			{/if}
		{:else}
			<span class="text-xs text-muted-foreground">—</span>
		{/if}
	</div>

	<!-- Tags -->
	<div class="hidden lg:flex items-center gap-1.5 flex-1 min-w-[200px]">
		{#if target.tags.length > 0}
			{#each target.tags.slice(0, 3) as tag}
				<Badge
					class="text-xs font-normal border"
					style="background-color: {tag.color}10; color: {tag.color}; border-color: {tag.color}30;"
				>
					{tag.name}
				</Badge>
			{/each}
			{#if target.tags.length > 3}
				<Badge variant="outline" class="text-xs font-normal">
					+{target.tags.length - 3}
				</Badge>
			{/if}
		{:else}
			<span class="text-xs text-muted-foreground">—</span>
		{/if}
	</div>

	<!-- Updated Time -->
	<div class="hidden sm:block text-xs text-muted-foreground w-[80px] text-right">
		{formatDistanceToNow(target.updated_at)}
	</div>

	<!-- Actions -->
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="h-8 w-8"
				>
					<Ellipsis class="h-4 w-4" />
					<span class="sr-only">Open menu</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-48">
			<DropdownMenu.Item onclick={() => onView(target)} class="gap-2">
				<Eye class="h-4 w-4" />
				View details
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => onEdit(target)} class="gap-2">
				<Pencil class="h-4 w-4" />
				Edit target
			</DropdownMenu.Item>
			<DropdownMenu.Separator />
			<DropdownMenu.Item
				onclick={() => onDelete(target)}
				class="gap-2 text-destructive focus:text-destructive"
			>
				<Trash2 class="h-4 w-4" />
				Delete target
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</div>
