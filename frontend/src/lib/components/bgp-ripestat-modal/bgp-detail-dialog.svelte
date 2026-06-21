<script lang="ts">
	import { targetsApi } from '$lib/api/targets';
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
		if (open && targetId && targetType) {
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
		if (!targetId) return;

		isLoadingOverview = true;
		isLoadingPrefixes = true;
		isLoadingPeers = true;
		overviewError = null;
		prefixesError = null;
		peersError = null;

		try {
			const d = await targetsApi.getBgp(targetId);
			overview = (d.as_overview as ASOverviewRead | null) ?? null;
			prefixes = (d.announced_prefixes as AnnouncedPrefixRead[]) ?? [];
			neighbours = (d.neighbours as ASNNeighbourRead[]) ?? [];
			networkInfo = (d.network_info as NetworkInfoRead[]) ?? null;
			abuseContact = d.abuse_contacts?.length
				? {
						resource: d.abuse_contacts[0].resource,
						abuse_emails: d.abuse_contacts.map((a) => a.abuse_email).filter(Boolean),
						rir: d.abuse_contacts[0].rir
					}
				: null;
			prefixOverview = (d.prefix_overview as PrefixOverviewRead[]) ?? null;
			relatedPrefixes = (d.related_prefixes as RelatedPrefixRead[]) ?? null;
		} catch (e) {
			overviewError = e instanceof Error ? e.message : 'Failed to load BGP data';
		} finally {
			isLoadingOverview = false;
			isLoadingPrefixes = false;
			isLoadingPeers = false;
		}
	}
</script>

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="sm:max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
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
									<Badge variant="secondary" class="text-[10px] h-5 min-w-5 px-1.5 ml-1">
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
									<Badge variant="secondary" class="text-[10px] h-5 min-w-5 px-1.5 ml-1">
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
