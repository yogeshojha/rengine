<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { TargetType, formatTargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import { getFreshnessLevel, relativeTime, formatShortDate } from '$lib/utilities/dates';
	import { getExternalLinksTargetDropdown } from '$lib/utilities/target-detail-external-links';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import EnrichmentPill from './enrichment-pill.svelte';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Globe from '@lucide/svelte/icons/globe';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Tag from '@lucide/svelte/icons/tag';
	import FileBracesCorner from '@lucide/svelte/icons/file-braces-corner';
	import FileSpreadsheet from '@lucide/svelte/icons/file-spreadsheet';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { TARGET_TYPE_ICONS } from '$lib/config/icons';

	interface Props {
		target: Target;
		onScan?: () => void;
		onRefreshEnrichment?: () => void;
		onExportJson?: () => void;
		onExportCsv?: () => void;
		onDelete?: () => void;
	}

	let { target, onScan, onRefreshEnrichment, onExportJson, onExportCsv, onDelete }: Props =
		$props();

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

	const lastEnrichedAt = $derived.by(() => {
		const timestamps = enrichmentSources
			.filter((e) => e.status === TaskStatus.SUCCESS && e.queriedAt)
			.map((e) => new Date(e.queriedAt!).getTime());
		if (timestamps.length === 0) return null;
		return new Date(Math.max(...timestamps)).toISOString();
	});

	const lastEnrichedFreshness = $derived(getFreshnessLevel(lastEnrichedAt));
</script>

<div class="space-y-4">
	<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
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
				<Badge variant="outline" class="gap-1 text-muted-foreground border-border/60">
					<TargetIcon class="h-3 w-3" />
					{formatTargetType(target.target_type)}
				</Badge>

				{#if target.organizations.length > 0 || target.tags.length > 0}
					<Separator orientation="vertical" class="h-4 mx-0.5" />
				{/if}

				{#each target.organizations as org (org.id ?? org.name)}
					<Badge variant="outline" class="gap-1">
						<Building2 class="h-3 w-3" />
						{org.name}
					</Badge>
				{/each}

				{#each target.tags as tag (tag.id ?? tag.name)}
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
				{#each enrichmentSources as enrichment (enrichment.label)}
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

				{#if lastEnrichedAt}
					<span class="text-xs text-muted-foreground">
						Last enriched {relativeTime(lastEnrichedAt)}
					</span>
					{#if lastEnrichedFreshness === 'stale'}
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Badge
										{...props}
										variant="outline"
										aria-label="Enrichment is stale — consider refreshing"
										class="text-[10px] h-4 px-1.5 border-warning/30 text-warning"
									>
										Stale
									</Badge>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content>Enrichment is stale — consider refreshing</Tooltip.Content>
						</Tooltip.Root>
					{/if}
				{:else}
					<span class="text-xs text-muted-foreground italic">Never enriched</span>
				{/if}

				{#if target.updated_at !== target.created_at}
					<span class="text-xs text-muted-foreground">·</span>
					<span class="text-xs text-muted-foreground">
						Updated {relativeTime(target.updated_at)}
					</span>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2 flex-wrap sm:shrink-0">
			<Button size="sm" class="gap-2" onclick={onScan}>
				<Play class="h-3.5 w-3.5" />
				Scan
			</Button>

			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							size="icon"
							class="h-9 w-9"
							aria-label="Refresh all enrichments"
							onclick={onRefreshEnrichment}
						>
							<RefreshCw class="h-4 w-4" />
						</Button>
					{/snippet}
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

					{#if externalLinks.length > 0}
						<DropdownMenu.Separator />
						<DropdownMenu.Label>External Lookup</DropdownMenu.Label>
						{#each externalLinks as link (link.url)}
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
</div>
