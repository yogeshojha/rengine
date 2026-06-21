<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { formatTargetType, TargetType } from '$lib/types/target';
	import { formatDate, formatDistanceToNow } from '$lib/utilities/dates';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import * as Dialog from '$lib/components/ui/dialog';
	import CopyButton from '@/components/copy-button.svelte';
	import {
		Building2,
		Calendar,
		Clock,
		Hash,
		History,
		Play,
		Tag as TagIcon,
		Trash2
	} from 'lucide-svelte';
	import { getTargetTypeIcon } from '$lib/config/icons';

	interface Props {
		open: boolean;
		target: Target | null;
		onOpenChange: (open: boolean) => void;
		onScan?: (target: Target) => void;
		onOpenHistory?: (target: Target) => void;
		onDelete?: (target: Target) => void;
	}

	let {
		open = $bindable(),
		target,
		onOpenChange,
		onScan,
		onOpenHistory,
		onDelete
	}: Props = $props();

	let TargetIcon = $derived(getTargetTypeIcon(target?.target_type ?? TargetType.DOMAIN));

	function handleScan() {
		if (target && onScan) {
			onScan(target);
		}
	}

	function handleOpenHistory() {
		if (target && onOpenHistory) {
			onOpenHistory(target);
			onOpenChange(false);
		}
	}

	function handleDelete() {
		if (target && onDelete) {
			onDelete(target);
			onOpenChange(false);
		}
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content
		class="sm:max-w-[520px] gap-0 p-0 overflow-hidden"
		onOpenAutoFocus={(e) => e.preventDefault()}
	>
		{#if target}
			<div class="p-6 pb-4">
				<div class="flex items-start justify-between gap-4">
					<div class="space-y-1 min-w-0">
						<Dialog.Title class="text-xl font-semibold">Target Details</Dialog.Title>
					</div>
				</div>
			</div>

			<Separator />

			<div class="p-6 space-y-6">
				<Badge variant="outline" class="gap-1 text-muted-foreground border-border/60 shrink-0 max-w-[180px]">
					<TargetIcon class="h-3 w-3 shrink-0" />
					<span class="truncate">{formatTargetType(target.target_type)}</span>
				</Badge>
				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium uppercase tracking-wider text-muted-foreground">
							Target Value
						</span>
						<Button variant="outline" size="sm" onclick={handleOpenHistory} class="h-7 gap-1.5 text-xs">
							<History class="h-3 w-3" />
							History
						</Button>
					</div>
					<div class="flex items-center gap-2 p-3 bg-muted/50 rounded-lg">
						<code class="flex-1 text-sm font-mono break-all">{target.target_value}</code>
						<CopyButton value={target.target_value} />
					</div>
				</div>

				{#if target.display_name}
					<div class="space-y-2">
						<span class="text-xs font-medium uppercase tracking-wider text-muted-foreground">
							Display Name
						</span>
						<p class="text-sm">{target.display_name}</p>
					</div>
				{/if}

				<div class="space-y-2">
					<div class="flex items-center gap-2">
						<Building2 class="h-3.5 w-3.5 text-muted-foreground" />
						<span class="text-xs font-medium uppercase tracking-wider text-muted-foreground">
							Organizations
						</span>
					</div>
					{#if target.organizations.length > 0}
						<div class="flex flex-wrap gap-2">
							{#each target.organizations as org (org.id ?? org.name)}
								<Badge variant="outline" class="font-normal">
									{org.name}
								</Badge>
							{/each}
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No organizations assigned</p>
					{/if}
				</div>

				<div class="space-y-2">
					<div class="flex items-center gap-2">
						<TagIcon class="h-3.5 w-3.5 text-muted-foreground" />
						<span class="text-xs font-medium uppercase tracking-wider text-muted-foreground">
							Tags
						</span>
					</div>
					{#if target.tags.length > 0}
						<div class="flex flex-wrap gap-2">
							{#each target.tags as tag (tag.id ?? tag.name)}
								<Badge
									variant="outline"
									class="font-normal"
									style="color: {tag.color}; border-color: {tag.color}40;"
								>
									{tag.name}
								</Badge>
							{/each}
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No tags assigned</p>
					{/if}
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
					<div class="space-y-1">
						<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
							<Calendar class="h-3 w-3" />
							<span>Created</span>
						</div>
						<p class="text-sm font-medium">{formatDate(target.created_at)}</p>
						<p class="text-xs text-muted-foreground">
							{formatDistanceToNow(target.created_at)} ago
						</p>
					</div>
					<div class="space-y-1">
						<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
							<Clock class="h-3 w-3" />
							<span>Last Updated</span>
						</div>
						<p class="text-sm font-medium">{formatDate(target.updated_at)}</p>
						<p class="text-xs text-muted-foreground">
							{formatDistanceToNow(target.updated_at)} ago
						</p>
					</div>
				</div>

				<div class="pt-2">
					<div
						class="flex items-center justify-between p-2 bg-muted/30 rounded border border-dashed"
					>
						<div class="flex items-center gap-2">
							<Hash class="h-3.5 w-3.5 text-muted-foreground" />
							<code class="text-xs text-muted-foreground font-mono">{target.id}</code>
						</div>
						<CopyButton value={target.id} />
					</div>
				</div>
			</div>

			<Separator />

			<div class="flex items-center justify-end gap-2 p-4 bg-muted/30">
				<Button onclick={handleScan} class="gap-2">
					<Play class="h-4 w-4" />
					Scan Target
				</Button>
				<Button variant="outline" size="sm" onclick={handleOpenHistory} class="gap-1.5">
					<History class="h-3.5 w-3.5" />
					History
				</Button>
				<Button variant="destructive" size="sm" onclick={handleDelete} class="gap-1.5">
					<Trash2 class="h-3.5 w-3.5" />
					Delete
				</Button>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
