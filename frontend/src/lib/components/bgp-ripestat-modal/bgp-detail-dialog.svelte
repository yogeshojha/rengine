<script lang="ts">
	import { ripestatApi } from '$lib/api/ripestat';
	import type {
		ASOverviewRead,
		ASNNeighbourRead,
		AnnouncedPrefixRead,
		NetworkInfoRead,
		AbuseContactRead,
		PrefixOverviewRead,
		RelatedPrefixRead
	} from '$lib/types/ripestat';
	import { TargetType } from '$lib/types/target';
	import type { BgpSummaryData } from '$lib/types/target';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import BgpOverviewTab from './bgp-overview-tab.svelte';
	import BgpPrefixesTab from './bgp-prefixes-tab.svelte';
	import BgpPeersTab from './bgp-peers-tab.svelte';
	import { RadioTower, Radio, Loader, TriangleAlert } from 'lucide-svelte';

	interface Props {
		open: boolean;
		targetId?: string | null;
		targetValue?: string | null;
		targetType?: TargetType | null;
		bgpSummary?: BgpSummaryData | null;
		onOpenChange: (open: boolean) => void;
		onAddAsTarget?: (value: string) => void;
	}

	let {
		open = $bindable(),
		targetId = null,
		targetValue = null,
		targetType = null,
		bgpSummary = null,
		onOpenChange,
		onAddAsTarget
	}: Props = $props();

	// Data state
	let overview = $state<ASOverviewRead | null>(null);
	let prefixes = $state<AnnouncedPrefixRead[]>([]);
	let neighbours = $state<ASNNeighbourRead[]>([]);
	let networkInfo = $state<NetworkInfoRead[] | null>(null);
	let abuseContact = $state<AbuseContactRead | null>(null);
	let prefixOverview = $state<PrefixOverviewRead[] | null>(null);
	let relatedPrefixes = $state<RelatedPrefixRead[] | null>(null);

	let isLoadingOverview = $state(false);
	let overviewError = $state<string | null>(null);

	let isLoadingPrefixes = $state(false);
	let prefixesError = $state<string | null>(null);

	let isLoadingPeers = $state(false);
	let peersError = $state<string | null>(null);

	let activeTab = $state('overview');

	let headerEl = $state<HTMLDivElement | null>(null);
	let tabListEl = $state<HTMLDivElement | null>(null);
	let scrollHeight = $state(0);

	let isAsn = $derived(targetType === 'asn');
	let isIp = $derived(targetType === 'ip');
	let isIpRange = $derived(targetType === 'ip_range');

	let DialogIcon = $derived(isAsn ? RadioTower : Radio);

	let displayTitle = $derived.by(() => {
		if (!targetValue) return 'BGP Details';
		return targetValue;
	});

	let displaySubtitle = $derived.by(() => {
		if (overview?.holder) return overview.holder;
		if (bgpSummary?.holder) return bgpSummary.holder;
		return 'BGP / Network Intelligence';
	});

	let showPrefixesTab = $derived(isAsn);
	let showPeersTab = $derived(isAsn);

	let prefixCount = $derived.by(() => {
		if (prefixes.length > 0) return prefixes.length;
		if (bgpSummary?.prefix_count != null) return bgpSummary.prefix_count;
		return 0;
	});

	let peerCount = $derived.by(() => {
		if (neighbours.length > 0) return neighbours.length;
		if (bgpSummary?.peer_count != null) return bgpSummary.peer_count;
		return 0;
	});

	function measureScrollHeight() {
		if (!headerEl || !tabListEl) return;
		requestAnimationFrame(() => {
			const viewportH = window.innerHeight;
			const dialogMaxH = Math.min(viewportH * 0.85, viewportH - 40);
			const headerH = headerEl?.offsetHeight ?? 0;
			const tabListH = tabListEl?.offsetHeight ?? 0;
			const available = dialogMaxH - headerH - tabListH;
			scrollHeight = Math.min(Math.max(available, 200), 500);
		});
	}

	$effect(() => {
		if (open && targetValue && targetType) {
			activeTab = 'overview';
			loadData();
		} else if (!open) {
			resetState();
		}
	});

	$effect(() => {
		if (open && headerEl && tabListEl) {
			measureScrollHeight();
		}
	});

	function resetState() {
		overview = null;
		prefixes = [];
		neighbours = [];
		networkInfo = null;
		abuseContact = null;
		prefixOverview = null;
		relatedPrefixes = null;
		overviewError = null;
		prefixesError = null;
		peersError = null;
		scrollHeight = 0;
	}

	async function loadData() {
		if (!targetValue || !targetType) return;

		if (targetType === 'asn') {
			await loadAsnData(targetValue);
		} else if (targetType === 'ip') {
			await loadIpData(targetValue);
		} else if (targetType === 'ip_range') {
			await loadIpRangeData(targetValue);
		}
	}

	async function loadAsnData(asn: string) {
		// Load overview + abuse in parallel (for overview tab)
		isLoadingOverview = true;
		overviewError = null;
		try {
			const [overviewResult, abuseResult] = await Promise.allSettled([
				ripestatApi.getASOverview(asn, true),
				ripestatApi.getAbuseContact(asn, true)
			]);
			if (overviewResult.status === 'fulfilled' && overviewResult.value) {
				overview = overviewResult.value.data as ASOverviewRead;
			}
			if (abuseResult.status === 'fulfilled' && abuseResult.value) {
				abuseContact = abuseResult.value.data as AbuseContactRead;
			}
		} catch (e) {
			overviewError = e instanceof Error ? e.message : 'Failed to load ASN overview';
		} finally {
			isLoadingOverview = false;
		}

		isLoadingPrefixes = true;
		isLoadingPeers = true;
		prefixesError = null;
		peersError = null;

		const [prefixResult, neighbourResult] = await Promise.allSettled([
			ripestatApi.getAnnouncedPrefixes(asn, true),
			ripestatApi.getASNNeighbours(asn, true)
		]);

		if (prefixResult.status === 'fulfilled' && prefixResult.value) {
			prefixes = (prefixResult.value.data as AnnouncedPrefixRead[]) ?? [];
		} else if (prefixResult.status === 'rejected') {
			prefixesError =
				prefixResult.reason instanceof Error
					? prefixResult.reason.message
					: 'Failed to load prefixes';
		}
		isLoadingPrefixes = false;

		if (neighbourResult.status === 'fulfilled' && neighbourResult.value) {
			neighbours = (neighbourResult.value.data as ASNNeighbourRead[]) ?? [];
		} else if (neighbourResult.status === 'rejected') {
			peersError =
				neighbourResult.reason instanceof Error
					? neighbourResult.reason.message
					: 'Failed to load peers';
		}
		isLoadingPeers = false;
	}

	async function loadIpData(ip: string) {
		isLoadingOverview = true;
		overviewError = null;
		try {
			const [networkResult, abuseResult] = await Promise.allSettled([
				ripestatApi.getNetworkInfo(ip, true),
				ripestatApi.getAbuseContact(ip, true)
			]);
			if (networkResult.status === 'fulfilled' && networkResult.value) {
				networkInfo = (networkResult.value.data as NetworkInfoRead[]) ?? [];
			}
			if (abuseResult.status === 'fulfilled' && abuseResult.value) {
				abuseContact = abuseResult.value.data as AbuseContactRead;
			}
		} catch (e) {
			overviewError = e instanceof Error ? e.message : 'Failed to load network info';
		} finally {
			isLoadingOverview = false;
		}
	}

	async function loadIpRangeData(prefix: string) {
		isLoadingOverview = true;
		overviewError = null;
		try {
			const [poResult, rpResult, abuseResult] = await Promise.allSettled([
				ripestatApi.getPrefixOverview(prefix, true),
				ripestatApi.getRelatedPrefixes(prefix, true),
				ripestatApi.getAbuseContact(prefix, true)
			]);
			if (poResult.status === 'fulfilled' && poResult.value) {
				prefixOverview = (poResult.value.data as PrefixOverviewRead[]) ?? [];
			}
			if (rpResult.status === 'fulfilled' && rpResult.value) {
				relatedPrefixes = (rpResult.value.data as RelatedPrefixRead[]) ?? [];
			}
			if (abuseResult.status === 'fulfilled' && abuseResult.value) {
				abuseContact = abuseResult.value.data as AbuseContactRead;
			}
		} catch (e) {
			overviewError = e instanceof Error ? e.message : 'Failed to load prefix info';
		} finally {
			isLoadingOverview = false;
		}
	}
</script>

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
		<div bind:this={headerEl} class="shrink-0">
			<Dialog.Header class="px-6 pt-6 pb-4">
				<div class="flex items-center gap-3">
					<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-primary/10 shrink-0">
						{#if isLoadingOverview && !bgpSummary}
							<Loader class="h-5 w-5 text-primary animate-spin" />
						{:else}
							<DialogIcon class="h-5 w-5 text-primary" />
						{/if}
					</div>
					<div class="min-w-0 flex-1">
						<Dialog.Title class="text-lg font-semibold font-mono truncate">
							{displayTitle}
						</Dialog.Title>
						<Dialog.Description class="text-sm text-muted-foreground truncate">
							{displaySubtitle}
						</Dialog.Description>
					</div>
				</div>
			</Dialog.Header>
		</div>

		{#if overviewError && !bgpSummary && !overview && !networkInfo && !prefixOverview}
			<Empty.Root>
				<Empty.Header>
					<Empty.Media variant="icon">
						<TriangleAlert />
					</Empty.Media>
					<Empty.Title>Failed to load BGP data</Empty.Title>
					<Empty.Description>{overviewError}</Empty.Description>
				</Empty.Header>
			</Empty.Root>
		{:else}
			<Tabs.Root bind:value={activeTab}>
				<div class="px-6 shrink-0" bind:this={tabListEl}>
					<Tabs.List class="w-full">
						<Tabs.Trigger value="overview" class="flex-1">Overview</Tabs.Trigger>
						{#if showPrefixesTab}
							<Tabs.Trigger value="prefixes" class="flex-1 gap-1.5">
								Prefixes
								{#if !isLoadingPrefixes && prefixCount > 0}
									<Badge
										variant="outline"
										class="text-[10px] h-5 min-w-5 px-1.5 ml-1 bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20"
									>
										{prefixCount.toLocaleString()}
									</Badge>
								{:else if isLoadingPrefixes}
									<Loader class="h-3 w-3 animate-spin text-muted-foreground ml-1" />
								{/if}
							</Tabs.Trigger>
						{/if}
						{#if showPeersTab}
							<Tabs.Trigger value="peers" class="flex-1 gap-1.5">
								Peers
								{#if !isLoadingPeers && peerCount > 0}
									<Badge
										variant="outline"
										class="text-[10px] h-5 min-w-5 px-1.5 ml-1 bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20"
									>
										{peerCount.toLocaleString()}
									</Badge>
								{:else if isLoadingPeers}
									<Loader class="h-3 w-3 animate-spin text-muted-foreground ml-1" />
								{/if}
							</Tabs.Trigger>
						{/if}
					</Tabs.List>
				</div>

				{#if scrollHeight > 0}
					<Tabs.Content value="overview">
						<ScrollArea style="height: {scrollHeight}px">
							<div class="px-6 py-5">
								<BgpOverviewTab
									targetValue={targetValue ?? ''}
									targetType={targetType ?? TargetType.IP}
									{overview}
									{networkInfo}
									{abuseContact}
									{prefixOverview}
									{relatedPrefixes}
									{bgpSummary}
									isLoading={isLoadingOverview}
									{onAddAsTarget}
								/>
							</div>
						</ScrollArea>
					</Tabs.Content>

					{#if showPrefixesTab}
						<Tabs.Content value="prefixes">
							<ScrollArea style="height: {scrollHeight}px">
								<div class="px-6 py-5">
									<BgpPrefixesTab
										{prefixes}
										isLoading={isLoadingPrefixes}
										error={prefixesError}
										{onAddAsTarget}
									/>
								</div>
							</ScrollArea>
						</Tabs.Content>
					{/if}

					{#if showPeersTab}
						<Tabs.Content value="peers">
							<ScrollArea style="height: {scrollHeight}px">
								<div class="px-6 py-5">
									<BgpPeersTab
										{neighbours}
										isLoading={isLoadingPeers}
										error={peersError}
										{onAddAsTarget}
									/>
								</div>
							</ScrollArea>
						</Tabs.Content>
					{/if}
				{/if}
			</Tabs.Root>
		{/if}
	</Dialog.Content>
</Dialog.Root>
