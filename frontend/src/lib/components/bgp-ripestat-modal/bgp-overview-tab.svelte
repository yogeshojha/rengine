<script lang="ts">
	import type {
		ASOverviewRead,
		NetworkInfoRead,
		AbuseContactRead,
		PrefixOverviewRead,
		RelatedPrefixRead
	} from '$lib/types/ripestat';
	import type { TargetType, BgpSummaryData } from '$lib/types/target';
	import { formatShortDate } from '$lib/utilities/dates';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import CopyButton from '@/components/copy-button.svelte';
	import {
		RadioTower,
		Radio,
		CircleCheck,
		CircleX,
		Mail,
		Shield,
		Blocks,
		Cable,
		Network,
		Globe,
		ArrowUpRight,
		CirclePlus,
	} from 'lucide-svelte';

	interface Props {
		targetValue: string;
		targetType: TargetType;
		overview: ASOverviewRead | null;
		networkInfo: NetworkInfoRead[] | null;
		abuseContact: AbuseContactRead | null;
		prefixOverview: PrefixOverviewRead[] | null;
		relatedPrefixes: RelatedPrefixRead[] | null;
		bgpSummary: BgpSummaryData | null;
		isLoading: boolean;
		onAddAsTarget?: (value: string) => void;
	}

	let {
		targetValue,
		targetType,
		overview,
		networkInfo,
		abuseContact,
		prefixOverview,
		relatedPrefixes,
		bgpSummary,
		onAddAsTarget
	}: Props = $props();

	let isAsn = $derived(targetType === 'asn');
	let isIp = $derived(targetType === 'ip');
	let isIpRange = $derived(targetType === 'ip_range');

	let TargetIcon = $derived(isAsn ? RadioTower : Radio);

	let displayHolder = $derived.by(() => {
		if (overview?.holder) return overview.holder;
		if (bgpSummary?.holder) return bgpSummary.holder;
		if (prefixOverview?.[0]?.holder) return prefixOverview[0].holder;
		return '';
	});

	let networkEntry = $derived(networkInfo?.[0] ?? null);

	let announcedStatus = $derived.by(() => {
		if (overview) return overview.announced;
		if (bgpSummary?.announced != null) return bgpSummary.announced;
		if (prefixOverview?.[0]) return prefixOverview[0].is_announced;
		return null;
	});

	let displayAsn = $derived.by(() => {
		if (networkEntry?.asn) return networkEntry.asn;
		if (bgpSummary?.asn) return bgpSummary.asn;
		if (prefixOverview?.[0]?.asn) return prefixOverview[0].asn;
		return null;
	});

	let displayPrefix = $derived.by(() => {
		if (networkEntry?.prefix) return networkEntry.prefix;
		if (bgpSummary?.prefix) return bgpSummary.prefix;
		return null;
	});

	let abuseEmails = $derived(abuseContact?.abuse_emails ?? []);

	let relatedCount = $derived(relatedPrefixes?.length ?? 0);

	let relatedByType = $derived.by(() => {
		if (!relatedPrefixes || relatedPrefixes.length === 0) return new Map();
		const map = new Map<string, RelatedPrefixRead[]>();
		for (const rp of relatedPrefixes) {
			const key = rp.relationship;
			if (!map.has(key)) map.set(key, []);
			map.get(key)!.push(rp);
		}
		return map;
	});

	const RELATIONSHIP_LABELS: Record<string, string> = {
		overlap: 'Overlapping',
		more_specific: 'More Specific',
		less_specific: 'Less Specific'
	};

	const RELATIONSHIP_COLORS: Record<string, string> = {
		overlap: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
		more_specific: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
		less_specific: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20'
	};

	function formatAsnLabel(asn: number): string {
		return `AS${asn}`;
	}

	function handleAddAsTarget(value: string) {
		onAddAsTarget?.(value);
	}
</script>

<div class="space-y-5 py-1">
	<!-- Identity -->
	<div class="flex items-start gap-3">
		<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-primary/10 shrink-0">
			<TargetIcon class="h-5 w-5 text-primary" />
		</div>
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<h3 class="text-lg font-semibold font-mono truncate">{targetValue}</h3>
				<CopyButton value={targetValue} />
			</div>
			{#if displayHolder}
				<p class="text-sm text-muted-foreground mt-0.5 truncate">{displayHolder}</p>
			{/if}
			<div class="flex items-center gap-2 mt-1.5">
				{#if isAsn}
					<Badge variant="outline" class="text-xs">ASN</Badge>
				{:else if isIp}
					<Badge variant="outline" class="text-xs">IP</Badge>
				{:else if isIpRange}
					<Badge variant="outline" class="text-xs">IP Range</Badge>
				{/if}
				{#if announcedStatus != null}
					{#if announcedStatus}
						<Badge
							class="text-xs gap-1 border bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
						>
							<CircleCheck class="h-3 w-3" />
							Announced
						</Badge>
					{:else}
						<Badge
							class="text-xs gap-1 border bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
						>
							<CircleX class="h-3 w-3" />
							Not Announced
						</Badge>
					{/if}
				{/if}
			</div>
		</div>
	</div>

	<Separator />

	<!-- Key facts grid -->
	<div class="grid grid-cols-2 gap-4">
		<!-- ASN-specific fields -->
		{#if isAsn && overview}
			{#if overview.rir}
				<div class="space-y-1">
					<div
						class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
					>
						<Globe class="h-3 w-3" />
						RIR
					</div>
					<p class="text-sm font-medium">{overview.rir}</p>
				</div>
			{/if}

			{#if overview.block_name}
				<div class="space-y-1">
					<div
						class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
					>
						<Blocks class="h-3 w-3" />
						Block
					</div>
					<p class="text-sm font-medium">{overview.block_name}</p>
					{#if overview.block_resource}
						<p class="text-xs text-muted-foreground font-mono">{overview.block_resource}</p>
					{/if}
				</div>
			{/if}
		{/if}

		<!-- IP-specific fields -->
		{#if isIp && displayAsn != null}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<RadioTower class="h-3 w-3" />
					Announcing ASN
				</div>
				<Tooltip.Root>
					<Tooltip.Trigger>
						<button
							class="text-sm font-medium font-mono text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
							onclick={() => handleAddAsTarget(formatAsnLabel(displayAsn!))}
						>
							{formatAsnLabel(displayAsn!)}
							<CirclePlus class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
						</button>
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>Add {formatAsnLabel(displayAsn!)} as target</p>
					</Tooltip.Content>
				</Tooltip.Root>
				{#if displayHolder}
					<p class="text-xs text-muted-foreground truncate">{displayHolder}</p>
				{/if}
			</div>

			{#if displayPrefix}
				<div class="space-y-1">
					<div
						class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
					>
						<Cable class="h-3 w-3" />
						Prefix
					</div>
					<Tooltip.Root>
						<Tooltip.Trigger>
							<button
								class="text-sm font-medium font-mono text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
								onclick={() => handleAddAsTarget(displayPrefix!)}
							>
								{displayPrefix}
								<CirclePlus class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
							</button>
						</Tooltip.Trigger>
						<Tooltip.Content>
							<p>Add {displayPrefix} as target</p>
						</Tooltip.Content>
					</Tooltip.Root>
				</div>
			{/if}
		{/if}

		<!-- IP_RANGE-specific fields -->
		{#if isIpRange && prefixOverview && prefixOverview.length > 0}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<RadioTower class="h-3 w-3" />
					Announcing ASN{prefixOverview.length > 1 ? 's' : ''}
				</div>
				{#each prefixOverview.slice(0, 3) as po}
					<Tooltip.Root>
						<Tooltip.Trigger>
							<button
								class="text-sm font-medium font-mono text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
								onclick={() => handleAddAsTarget(formatAsnLabel(po.asn))}
							>
								{formatAsnLabel(po.asn)}
								<CirclePlus class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
							</button>
						</Tooltip.Trigger>
						<Tooltip.Content>
							<p>Add {formatAsnLabel(po.asn)} as target</p>
						</Tooltip.Content>
					</Tooltip.Root>
					{#if po.holder}
						<p class="text-xs text-muted-foreground truncate">{po.holder}</p>
					{/if}
				{/each}
			</div>
		{/if}

		<!-- Quick stats for ASN targets -->
		{#if isAsn && bgpSummary}
			{#if bgpSummary.prefix_count != null}
				<div class="space-y-1">
					<div
						class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
					>
						<Network class="h-3 w-3" />
						Announced Prefixes
					</div>
					<p class="text-sm font-medium">{bgpSummary.prefix_count.toLocaleString()}</p>
				</div>
			{/if}

			{#if bgpSummary.peer_count != null}
				<div class="space-y-1">
					<div
						class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
					>
						<ArrowUpRight class="h-3 w-3" />
						BGP Peers
					</div>
					<p class="text-sm font-medium">{bgpSummary.peer_count.toLocaleString()}</p>
				</div>
			{/if}
		{/if}
	</div>

	<!-- Abuse contacts -->
	{#if abuseEmails.length > 0}
		<Separator />
		<div>
			<div
				class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider mb-2"
			>
				<Shield class="h-3 w-3" />
				Abuse Contact{abuseEmails.length > 1 ? 's' : ''}
			</div>
			<div class="flex flex-wrap gap-1.5">
				{#each abuseEmails as email}
					<div class="flex items-center gap-1.5">
						<Mail class="h-3 w-3 text-muted-foreground" />
						<a
							href="mailto:{email}"
							class="text-sm text-muted-foreground hover:text-foreground transition-colors"
						>
							{email}
						</a>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Related prefixes summary for IP_RANGE -->
	{#if isIpRange && relatedCount > 0}
		<Separator />
		<div>
			<div
				class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider mb-3"
			>
				<Cable class="h-3 w-3" />
				Related Prefixes
				<Badge variant="outline" class="text-[10px] h-5 min-w-5 px-1.5 ml-0.5">
					{relatedCount}
				</Badge>
			</div>
			<div class="space-y-2">
				{#each [...relatedByType.entries()].slice(0, 3) as [relationship, prefixes]}
					<div class="space-y-1.5">
						<Badge
							class="text-[10px] font-normal border {RELATIONSHIP_COLORS[relationship] ??
								'bg-muted text-muted-foreground border-border'}"
						>
							{RELATIONSHIP_LABELS[relationship] ?? relationship}
							<span class="ml-1 opacity-70">({prefixes.length})</span>
						</Badge>
						<div class="flex flex-wrap gap-1.5 ml-1">
							{#each prefixes.slice(0, 4) as rp}
								<Tooltip.Root>
									<Tooltip.Trigger>
										<button
											class="cursor-pointer"
											onclick={() => handleAddAsTarget(rp.related_prefix)}
										>
											<Badge
												variant="outline"
												class="text-xs font-mono font-normal gap-1.5 hover:bg-accent hover:border-primary/30 transition-colors"
											>
												{rp.related_prefix}
												{#if rp.origin_asn}
													<span class="text-muted-foreground">
														AS{rp.origin_asn}
													</span>
												{/if}
												<CirclePlus class="h-3 w-3 text-muted-foreground opacity-60" />
											</Badge>
										</button>
									</Tooltip.Trigger>
									<Tooltip.Content>
										<p>Add {rp.related_prefix} as target</p>
									</Tooltip.Content>
								</Tooltip.Root>
							{/each}
							{#if prefixes.length > 4}
								<Badge variant="outline" class="text-[10px] font-normal text-muted-foreground">
									+{prefixes.length - 4} more
								</Badge>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Footer -->
	{#if bgpSummary?.queried_at}
		<Separator />
		<p class="text-xs text-muted-foreground">
			Last queried {formatShortDate(bgpSummary.queried_at)}
			{#if abuseContact?.rir}
				· RIR: {abuseContact.rir}
			{/if}
		</p>
	{/if}
</div>
