<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { formatDistanceToNow } from '$lib/utilities/dates';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '@/components/copy-button.svelte';
	import WhoisInline from '$lib/components/targets/whois-inline.svelte';
	import BgpInline from '$lib/components/targets/bgp-inline.svelte';
	import DiscoveryBadge from '$lib/components/viewdns-discoveries/discovery-badge.svelte';
	import { Ellipsis, Eye, History, Pencil, Play, Trash2 } from 'lucide-svelte';
	import TargetOrgPopover from '$lib/components/targets/target-org-popover.svelte';
	import TargetTagPopover from '$lib/components/targets/target-tag-popover.svelte';

	interface Props {
		target: Target;
		isScanning: boolean;
		isSelected: boolean;
		onSelect: (targetId: string) => void;
		onScan: (target: Target) => void;
		onOpenHistory: (target: Target) => void;
		onView: (target: Target) => void;
		onEdit: (target: Target) => void;
		onDelete: (target: Target) => void;
		onWhoisClick: (target: Target) => void;
		onDiscoveriesClick?: (target: Target) => void;
		onBgpClick?: (target: Target) => void;
	}

	let {
		target,
		isScanning,
		isSelected,
		onSelect,
		onScan,
		onOpenHistory,
		onView,
		onEdit,
		onDelete,
		onWhoisClick,
		onDiscoveriesClick,
		onBgpClick
	}: Props = $props();

	// TODO: dummy scan count, fetch later
	const scanCount = 5;
</script>

<div
	class="group flex items-center gap-3 px-4 py-3 border-b border-border/50 transition-colors {isSelected
		? 'bg-primary/5 hover:bg-primary/10'
		: 'hover:bg-muted/30'}"
>
	<Checkbox
		checked={isSelected}
		onCheckedChange={() => onSelect(target.id)}
		class="transition-opacity {isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}"
	/>

	<!-- Target identity + WHOIS inline + BGP inline + Discovery badge -->
	<div class="w-[260px] min-w-0 space-y-0.5">
		<div class="flex items-center gap-2">
			<span class="font-mono text-sm font-medium truncate">{target.target_value}</span>
			<CopyButton
				value={target.target_value}
				class="opacity-0 group-hover:opacity-100 transition-opacity"
			/>
		</div>
		{#if target.display_name && target.display_name !== target.target_value}
			<p class="text-xs text-muted-foreground truncate">{target.display_name}</p>
		{/if}
		<div class="items-center gap-2">
			<WhoisInline
				status={target.whois_status}
				whois={target.whois}
				error={target.whois_error}
				onClick={() => onWhoisClick(target)}
			/>
			<BgpInline
				status={target.bgp_status}
				bgp={target.bgp}
				targetType={target.target_type}
				targetValue={target.target_value}
				onClick={() => onBgpClick?.(target)}
			/>

			<DiscoveryBadge
				targetValue={target.target_value}
				targetType={target.target_type}
				whois={target.whois}
				onClick={() => onDiscoveriesClick?.(target)}
			/>
		</div>
	</div>

	<div class="w-[120px]">
		{#if scanCount > 0}
			<button
				onclick={() => onOpenHistory(target)}
				class="relative inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 hover:bg-sky-500/15 transition-colors"
			>
				<History class="h-3 w-3" />
				{scanCount} scans

				{#if !isScanning}
					<!-- TODO: replace with real scanning status -->
					<span class="absolute -right-1 top-1/2 -translate-y-1/2 flex h-2 w-2">
						<span
							class="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"
						></span>
						<span class="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
					</span>
				{/if}
			</button>
		{:else}
			<span class="text-xs text-muted-foreground">—</span>
		{/if}
	</div>

	<!-- Organizations -->
	<div class="hidden md:flex items-center flex-1 min-w-[180px]">
		<TargetOrgPopover targetId={target.id} currentOrgs={target.organizations} />
	</div>

	<!-- Tags -->
	<div class="hidden lg:flex items-center flex-1 min-w-[200px]">
		<TargetTagPopover targetId={target.id} currentTags={target.tags} />
	</div>

	<div class="hidden sm:block text-xs text-muted-foreground w-[80px] text-right">
		{formatDistanceToNow(target.updated_at)}
	</div>

	<div class="flex items-center gap-1">
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
						onclick={() => onScan(target)}
					>
						<Play class="h-4 w-4 text-blue-400" />
					</Button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content>
				<p>Scan target</p>
			</Tooltip.Content>
		</Tooltip.Root>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="ghost" size="icon" class="h-8 w-8">
						<Ellipsis class="h-4 w-4" />
						<span class="sr-only">Open menu</span>
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-48">
				<DropdownMenu.Item onclick={() => onScan(target)} class="gap-2">
					<Play class="h-4 w-4 text-blue-500" />
					Scan target
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => onOpenHistory(target)} class="gap-2">
					<History class="h-4 w-4" />
					Scan history
				</DropdownMenu.Item>

				<DropdownMenu.Separator />

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
</div>
