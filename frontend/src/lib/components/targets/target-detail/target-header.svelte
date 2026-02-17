<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { TargetType, getTargetTypeColor, formatTargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import {
		getFreshnessLevel,
		getFreshnessColors,
		relativeTime,
		formatShortDate
	} from '$lib/utilities/dates';
	import { getExternalLinksTargetDropdown } from '$lib/utilities/target-detail-external-links';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import EnrichmentPill from './enrichment-pill.svelte';
	import {
		Play,
		RotateCcw,
		Ellipsis,
		Globe,
		Building2,
		Tag,
		FileBracesCorner,
		FileSpreadsheet,
		ExternalLink,
		Trash2,
		StickyNote,
		Activity,
		Layers,
		GitBranch,
		History
	} from 'lucide-svelte';
	import { TARGET_TYPE_ICONS } from '$lib/config/icons';

	interface Props {
		target: Target;
		activeTab?: string;
		onScan?: () => void;
		onRefreshEnrichment?: () => void;
		onExportJson?: () => void;
		onExportCsv?: () => void;
		onDelete?: () => void;
		onTabChange?: (tab: string) => void;
	}

	let {
		target,
		activeTab = 'overview',
		onScan,
		onRefreshEnrichment,
		onExportJson,
		onExportCsv,
		onDelete,
		onTabChange
	}: Props = $props();

	const TargetIcon = $derived(TARGET_TYPE_ICONS[target.target_type] || Globe);

	const enrichmentSources = $derived(
		[
			{
				label: 'DNS',
				status: target.dns_status,
				queriedAt: target.dns?.queried_at ?? null,
				applicable: [TargetType.DOMAIN, TargetType.URL].includes(target.target_type)
			},
			{
				label: 'WHOIS',
				status: target.whois_status,
				queriedAt: target.whois?.queried_at ?? null,
				applicable: true
			},
			{
				label: 'BGP',
				status: target.bgp_status,
				queriedAt: target.bgp?.queried_at ?? null,
				applicable: [TargetType.IP, TargetType.IP_RANGE, TargetType.ASN].includes(
					target.target_type
				)
			}
		].filter((e) => e.applicable)
	);

	const externalLinks = $derived(
		getExternalLinksTargetDropdown(target.target_value, target.target_type)
	);

	// Last scanned = most recent successful enrichment timestamp
	// TODO: Will be replaced by actual scan_history timestamp when API is ready
	const lastScannedAt = $derived.by(() => {
		const timestamps = enrichmentSources
			.filter((e) => e.status === TaskStatus.SUCCESS && e.queriedAt)
			.map((e) => new Date(e.queriedAt!).getTime());
		if (timestamps.length === 0) return null;
		return new Date(Math.max(...timestamps)).toISOString();
	});

	const lastScannedFreshness = $derived(getFreshnessLevel(lastScannedAt));
	const lastScannedColor = $derived(getFreshnessColors(lastScannedFreshness));

	// define all tabs here
	const tabs = [
		{ value: 'overview', label: 'Overview', icon: Activity },
		{ value: 'enrichment', label: 'Enrichment', icon: Layers },
		{ value: 'correlation', label: 'Correlation', icon: GitBranch },
		{ value: 'history', label: 'History', icon: History }
	] as const;
</script>

<div class="space-y-4">
	<div class="flex items-start justify-between gap-6">
		<div class="space-y-3 min-w-0 flex-1">
			<div class="flex items-center gap-3">
				<div class="h-10 w-10 rounded-lg border bg-muted flex items-center justify-center shrink-0">
					<TargetIcon class="h-5 w-5 text-muted-foreground" />
				</div>
				<div class="min-w-0">
					<div class="flex items-center gap-2">
						<h1 class="text-xl font-semibold tracking-tight font-mono truncate">
							{target.target_value}
						</h1>
						<CopyButton value={target.target_value} />
					</div>
					{#if target.display_name}
						<p class="text-sm text-muted-foreground">{target.display_name}</p>
					{/if}
				</div>
			</div>

			<div class="flex items-center gap-1.5 flex-wrap">
				<Badge variant="outline" class={getTargetTypeColor(target.target_type)}>
					{formatTargetType(target.target_type)}
				</Badge>

				{#if target.organizations.length > 0 || target.tags.length > 0}
					<Separator orientation="vertical" class="h-4 mx-0.5" />
				{/if}

				{#each target.organizations as org}
					<Badge variant="outline" class="gap-1">
						<Building2 class="h-3 w-3" />
						{org.name}
					</Badge>
				{/each}

				{#each target.tags as tag}
					<Badge
						variant="outline"
						class="gap-1"
						style="border-color: {tag.color}40; color: {tag.color}"
					>
						<Tag class="h-3 w-3" />
						{tag.name}
					</Badge>
				{/each}
			</div>

			<div class="flex items-center gap-2 flex-wrap">
				{#each enrichmentSources as enrichment}
					<EnrichmentPill
						label={enrichment.label}
						status={enrichment.status}
						queriedAt={enrichment.queriedAt}
					/>
				{/each}

				<Separator orientation="vertical" class="h-4 mx-0.5" />

				<span class="text-xs text-muted-foreground">
					Added {formatShortDate(target.created_at)}
				</span>

				<span class="text-xs text-muted-foreground">·</span>

				{#if lastScannedAt}
					<span class="text-xs font-medium {lastScannedColor.text}">
						Last scanned {relativeTime(lastScannedAt)}
					</span>
					{#if lastScannedFreshness === 'stale'}
						<Badge
							variant="outline"
							class="text-[10px] h-4 px-1.5 border-amber-500/30 text-amber-600 dark:text-amber-400"
						>
							Stale
						</Badge>
					{/if}
				{:else}
					<span class="text-xs text-muted-foreground italic">Never scanned</span>
				{/if}

				{#if target.updated_at !== target.created_at}
					<span class="text-xs text-muted-foreground">·</span>
					<span class="text-xs text-muted-foreground">
						Updated {relativeTime(target.updated_at)}
					</span>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2 shrink-0">
			<Button size="sm" class="gap-2 bg-blue-600 hover:bg-blue-700 text-white" onclick={onScan}>
				<Play class="h-3.5 w-3.5" />
				Scan
			</Button>

			<Tooltip.Root>
				<Tooltip.Trigger>
					<Button variant="outline" size="icon" class="h-9 w-9" onclick={onRefreshEnrichment}>
						<RotateCcw class="h-4 w-4" />
					</Button>
				</Tooltip.Trigger>
				<Tooltip.Content>Refresh all enrichments</Tooltip.Content>
			</Tooltip.Root>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="icon" class="h-9 w-9">
							<Ellipsis class="h-4 w-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-52">
					<DropdownMenu.Label>Export</DropdownMenu.Label>
					<DropdownMenu.Item onclick={onExportJson}>
						<FileBracesCorner class="h-4 w-4 mr-2" />
						Export as JSON
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={onExportCsv}>
						<FileSpreadsheet class="h-4 w-4 mr-2" />
						Export as CSV
					</DropdownMenu.Item>

					<DropdownMenu.Separator />
					<DropdownMenu.Item>
						<StickyNote class="h-4 w-4 mr-2" />
						Add Note
					</DropdownMenu.Item>

					{#if externalLinks.length > 0}
						<DropdownMenu.Separator />
						<DropdownMenu.Label>External Lookup</DropdownMenu.Label>
						{#each externalLinks as link}
							<DropdownMenu.Item
								onclick={() => window.open(link.url, '_blank', 'noopener,noreferrer')}
							>
								<ExternalLink class="h-4 w-4 mr-2" />
								{link.label}
							</DropdownMenu.Item>
						{/each}
					{/if}

					<DropdownMenu.Separator />
					<DropdownMenu.Item class="text-destructive focus:text-destructive" onclick={onDelete}>
						<Trash2 class="h-4 w-4 mr-2" />
						Delete Target
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>

	<Tabs.Root
		value={activeTab}
		onValueChange={(v) => {
			if (v && onTabChange) onTabChange(v);
		}}
	>
		<Tabs.List>
			{#each tabs as tab}
				{@const TabIcon = tab.icon}
				<Tabs.Trigger value={tab.value} class="gap-1.5">
					<TabIcon class="h-3.5 w-3.5" />
					{tab.label}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>
	</Tabs.Root>
</div>
