<script lang="ts">
	import { TargetType, getTargetTypeColor, formatTargetType, type Target } from '$lib/types/target';
	import { formatDistanceToNow, getColorsForTimestamp } from '$lib/utilities/dates';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Input } from '$lib/components/ui/input';
	import { goto } from '$app/navigation';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '@/components/copy-button.svelte';
	import WhoisInline from '$lib/components/targets/whois-inline.svelte';
	import BgpInline from '$lib/components/targets/bgp-inline.svelte';
	import DnsInline from '$lib/components/targets/dns-inline.svelte';
	import DiscoveryBadge from '$lib/components/viewdns-discoveries/discovery-badge.svelte';
	import TargetInfraBadge from '$lib/components/targets/target-infra-badge.svelte';
	import { Ellipsis, Eye, History, Loader, Pencil, Play, RefreshCw, Trash2 } from 'lucide-svelte';
	import TargetOrgPopover from '$lib/components/targets/target-org-popover.svelte';
	import TargetTagPopover from '$lib/components/targets/target-tag-popover.svelte';
	import { stopProp } from '$lib/utilities';

	type EnrichmentKind = 'whois' | 'dns' | 'bgp';

	interface Props {
		target: Target;
		isScanning: boolean;
		isSelected: boolean;
		onSelect: (targetId: string) => void;
		onScan: (target: Target) => void;
		onOpenHistory: (target: Target) => void;
		onView: (target: Target) => void;
		onDelete: (target: Target) => void;
		onRename: (target: Target, name: string) => void;
		onReEnrich: (target: Target, kind: EnrichmentKind) => void;
		onWhoisClick: (target: Target) => void;
		onDiscoveriesClick?: (target: Target) => void;
		onBgpClick?: (target: Target) => void;
		onInfraClick?: (target: Target) => void;
	}

	let {
		target,
		isScanning,
		isSelected,
		onSelect,
		onScan,
		onOpenHistory,
		onView,
		onDelete,
		onRename,
		onReEnrich,
		onWhoisClick,
		onDiscoveriesClick,
		onBgpClick,
		onInfraClick
	}: Props = $props();

	let editing = $state(false);
	let editValue = $state('');

	let canDns = $derived(
		target.target_type === TargetType.DOMAIN || target.target_type === TargetType.URL
	);
	let canBgp = $derived(
		target.target_type === TargetType.IP ||
			target.target_type === TargetType.IP_RANGE ||
			target.target_type === TargetType.ASN
	);

	let freshness = $derived(getColorsForTimestamp(target.updated_at));

	function startRename() {
		editValue = target.display_name || target.target_value;
		editing = true;
	}

	function commitRename() {
		const next = editValue.trim();
		if (next && next !== target.display_name) onRename(target, next);
		editing = false;
	}
</script>

<div
	class="group flex items-center gap-3 px-4 py-2.5 border-b border-border/50 transition-colors cursor-pointer {isSelected
		? 'bg-primary/5 hover:bg-primary/10'
		: 'hover:bg-muted/30'}"
	onclick={() => goto(`/targets/${target.id}`)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			goto(`/targets/${target.id}`);
		}
	}}
	role="button"
	tabindex="0"
>
	<Checkbox
		checked={isSelected}
		onCheckedChange={() => onSelect(target.id)}
		class="transition-opacity {isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}"
	/>

	<!-- TARGET -->
	<div class="w-[210px] min-w-0">
		<div class="flex items-center gap-2">
			<span class="font-mono text-sm font-medium truncate">{target.target_value}</span>
			<CopyButton
				value={target.target_value}
				class="opacity-0 group-hover:opacity-100 transition-opacity"
			/>
		</div>
		{#if editing}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div onclick={stopProp}>
				<Input
					value={editValue}
					oninput={(e) => (editValue = e.currentTarget.value)}
					onblur={commitRename}
					onkeydown={(e) => {
						if (e.key === 'Enter') commitRename();
						else if (e.key === 'Escape') editing = false;
					}}
					autofocus
					class="mt-0.5 h-6 text-xs"
					placeholder="Display name"
				/>
			</div>
		{:else if target.display_name && target.display_name !== target.target_value}
			<p class="text-xs text-muted-foreground truncate">{target.display_name}</p>
		{/if}
	</div>

	<!-- TYPE -->
	<div class="hidden w-[84px] sm:block">
		<span
			class="inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium {getTargetTypeColor(
				target.target_type
			)}"
		>
			{formatTargetType(target.target_type)}
		</span>
	</div>

	<!-- WHOIS / registrar + expiry -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="hidden min-w-[160px] flex-1 items-center lg:flex" onclick={stopProp}>
		<WhoisInline
			status={target.whois_status}
			whois={target.whois}
			error={target.whois_error}
			targetId={target.id}
			onClick={() => onWhoisClick(target)}
		/>
	</div>

	<!-- RECORDS (DNS for domains, BGP for IP/ASN) -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="hidden w-[150px] items-center xl:flex" onclick={stopProp}>
		<DnsInline
			status={target.dns_status}
			dns={target.dns}
			targetType={target.target_type}
			targetValue={target.target_value}
			targetId={target.id}
			onClick={() => onView(target)}
		/>
		<BgpInline
			status={target.bgp_status}
			bgp={target.bgp}
			targetType={target.target_type}
			targetValue={target.target_value}
			onClick={() => onBgpClick?.(target)}
		/>
	</div>

	<!-- RELATED (shared infra + discoveries) -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="hidden w-[110px] items-center gap-2 xl:flex" onclick={stopProp}>
		<TargetInfraBadge
			targetId={target.id}
			whoisRecordId={target.whois_record_id}
			onClick={() => onInfraClick?.(target)}
		/>
		<DiscoveryBadge
			targetValue={target.target_value}
			targetType={target.target_type}
			whois={target.whois}
			onClick={() => onDiscoveriesClick?.(target)}
		/>
	</div>

	<!-- Organizations -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="hidden flex-1 items-center md:flex min-w-[130px]">
		<div onclick={stopProp} class="inline-flex">
			<TargetOrgPopover targetId={target.id} currentOrgs={target.organizations} />
		</div>
	</div>

	<!-- Tags -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="hidden flex-1 items-center lg:flex min-w-[130px]" onclick={stopProp}>
		<div onclick={stopProp} class="inline-flex">
			<TargetTagPopover targetId={target.id} currentTags={target.tags} />
		</div>
	</div>

	<!-- UPDATED -->
	<div
		class="hidden w-[84px] items-center justify-end gap-1.5 text-right text-xs text-muted-foreground sm:flex"
	>
		<span class="h-1.5 w-1.5 rounded-full shrink-0 {freshness.dot}"></span>
		{formatDistanceToNow(target.updated_at)}
	</div>

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="flex items-center gap-1" onclick={stopProp}>
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
						{#if isScanning}
							<Loader class="h-4 w-4 animate-spin text-blue-400" />
						{:else}
							<Play class="h-4 w-4 text-blue-400" />
						{/if}
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
				<DropdownMenu.Item onclick={() => onOpenHistory(target)} class="gap-2">
					<History class="h-4 w-4" />
					Scan history
				</DropdownMenu.Item>

				<DropdownMenu.Item onclick={() => onView(target)} class="gap-2">
					<Eye class="h-4 w-4" />
					View Summary
				</DropdownMenu.Item>

				<DropdownMenu.Item onclick={startRename} class="gap-2">
					<Pencil class="h-4 w-4" />
					Rename
				</DropdownMenu.Item>

				<DropdownMenu.Separator />

				<DropdownMenu.Item onclick={() => onReEnrich(target, 'whois')} class="gap-2">
					<RefreshCw class="h-4 w-4" />
					Re-run WHOIS
				</DropdownMenu.Item>
				{#if canDns}
					<DropdownMenu.Item onclick={() => onReEnrich(target, 'dns')} class="gap-2">
						<RefreshCw class="h-4 w-4" />
						Re-run DNS
					</DropdownMenu.Item>
				{/if}
				{#if canBgp}
					<DropdownMenu.Item onclick={() => onReEnrich(target, 'bgp')} class="gap-2">
						<RefreshCw class="h-4 w-4" />
						Re-run BGP
					</DropdownMenu.Item>
				{/if}

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
