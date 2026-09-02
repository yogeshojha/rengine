<script lang="ts">
	import { whoisApi } from '$lib/api/whois';
	import type { WhoisRecordRead, WhoisCorrelationResult } from '$lib/types/whois';
	import { TargetType } from '$lib/types/target';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Empty from '$lib/components/ui/empty';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { toast } from 'svelte-sonner';
	import WhoisOverviewTab from './whois-overview-tab.svelte';
	import WhoisEntitiesTab from './whois-entities-tab.svelte';
	import WhoisRelatedTab from './whois-related-tab.svelte';
	import CorrelationLookupDialog from './correlation-lookup-dialog.svelte';
	import DiscoveriesSummary from '$lib/components/viewdns-discoveries/discoveries-summary.svelte';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getLookupTypeIcon } from '$lib/config/icons';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		open: boolean;
		recordId?: string | null;
		targetId?: string;
		record?: WhoisRecordRead | null;
		targetValue?: string | null;
		targetType?: TargetType | null;
		initialTab?: string;
		onOpenChange: (open: boolean) => void;
		onOpenTargetSummary?: () => void;
	}

	let {
		open = $bindable(),
		recordId = null,
		targetId,
		record: externalRecord = null,
		targetValue = null,
		targetType = null,
		initialTab = 'overview',
		onOpenChange,
		onOpenTargetSummary
	}: Props = $props();

	let internalRecord = $state<WhoisRecordRead | null>(null);
	let isLoadingRecord = $state(false);
	let recordError = $state<string | null>(null);

	let correlations = $state<WhoisCorrelationResult[]>([]);
	let isLoadingCorrelations = $state(false);
	let correlationsError = $state<string | null>(null);

	let isRefreshing = $state(false);
	let activeTab = $state('overview');

	let showCorrelationLookup = $state(false);
	let correlationLookupType = $state('');
	let correlationLookupValue = $state('');

	let displayRecord = $derived(internalRecord ?? externalRecord);

	let hasEntities = $derived(
		displayRecord?.parsed_data?.entities != null &&
			Object.values(displayRecord.parsed_data.entities).some((arr) => arr && arr.length > 0)
	);

	let relatedCount = $derived.by(() => {
		const seen = new SvelteSet<string>();
		for (const c of correlations) {
			for (const r of c.records) {
				if (r.id !== displayRecord?.id) seen.add(r.id);
			}
		}
		return seen.size;
	});

	let LookupIcon = $derived(getLookupTypeIcon(displayRecord?.lookup_type ?? ''));

	let showDiscoveriesTab = $derived(
		targetValue != null && (targetType === TargetType.DOMAIN || targetType === TargetType.IP)
	);

	let headerEl = $state<HTMLDivElement | null>(null);
	let tabListEl = $state<HTMLDivElement | null>(null);
	let scrollHeight = $state(0);

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
		if (open) {
			activeTab = initialTab;
			loadData();
		} else {
			internalRecord = null;
			correlations = [];
			recordError = null;
			correlationsError = null;
			scrollHeight = 0;
		}
	});

	$effect(() => {
		if (open && displayRecord && headerEl && tabListEl) {
			measureScrollHeight();
		}
	});

	async function loadCorrelations() {
		if (!targetId) return;
		isLoadingCorrelations = true;
		correlationsError = null;
		try {
			correlations = await whoisApi.getTargetCorrelations(targetId);
		} catch (e) {
			correlationsError = e instanceof Error ? e.message : 'Failed to load correlations';
		} finally {
			isLoadingCorrelations = false;
		}
	}

	async function loadData() {
		if (!externalRecord && recordId) {
			isLoadingRecord = true;
			recordError = null;
			try {
				internalRecord = await whoisApi.getRecord(recordId);
			} catch (e) {
				recordError = e instanceof Error ? e.message : 'Failed to load WHOIS record';
			} finally {
				isLoadingRecord = false;
			}
		}

		await loadCorrelations();
	}

	async function handleRefresh() {
		const id = displayRecord?.id;
		if (!id) return;

		isRefreshing = true;
		try {
			const response = await whoisApi.refreshRecord(id);
			internalRecord = response.record;
			await loadCorrelations();
			toast.success('WHOIS record refreshed');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to refresh WHOIS record');
		} finally {
			isRefreshing = false;
		}
	}

	function handleCorrelationClick(type: string, value: string) {
		correlationLookupType = type;
		correlationLookupValue = value;
		showCorrelationLookup = true;
	}
</script>

<Dialog.Root bind:open {onOpenChange}>
	<Dialog.Content class="sm:max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
		<div bind:this={headerEl} class="shrink-0">
			<Dialog.Header class="px-6 pt-6 pb-4">
				<div class="flex items-center gap-3">
					<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-primary/10 shrink-0">
						{#if isLoadingRecord}
							<Spinner class="h-5 w-5 text-primary" />
						{:else}
							<LookupIcon class="h-5 w-5 text-primary" />
						{/if}
					</div>
					<div class="min-w-0 flex-1">
						<Dialog.Title class="text-lg font-semibold truncate">
							{#if displayRecord}
								{displayRecord.name || displayRecord.query_value}
							{:else if isLoadingRecord}
								Loading…
							{:else}
								WHOIS Record
							{/if}
						</Dialog.Title>
						<Dialog.Description class="text-sm text-muted-foreground">
							WHOIS / RDAP record details
						</Dialog.Description>
					</div>
					{#if displayRecord}
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon"
										class="h-8 w-8 shrink-0"
										onclick={handleRefresh}
										disabled={isRefreshing}
									>
										<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
									</Button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content>
								<p>Refresh WHOIS data</p>
							</Tooltip.Content>
						</Tooltip.Root>
					{/if}
				</div>
			</Dialog.Header>
		</div>

		{#if isLoadingRecord && !displayRecord}
			<Empty.Root>
				<Empty.Header>
					<Empty.Media variant="icon">
						<Spinner />
					</Empty.Media>
					<Empty.Title>Loading WHOIS record…</Empty.Title>
				</Empty.Header>
			</Empty.Root>
		{:else if recordError}
			<Empty.Root>
				<Empty.Header>
					<Empty.Media variant="icon">
						<TriangleAlert />
					</Empty.Media>
					<Empty.Title>Failed to load record</Empty.Title>
					<Empty.Description>{recordError}</Empty.Description>
				</Empty.Header>
			</Empty.Root>
		{:else if displayRecord}
			<Tabs.Root bind:value={activeTab}>
				<div class="px-6 shrink-0" bind:this={tabListEl}>
					<Tabs.List class="w-full">
						<Tabs.Trigger value="overview" class="flex-1">Overview</Tabs.Trigger>
						{#if hasEntities}
							<Tabs.Trigger value="entities" class="flex-1">Entities</Tabs.Trigger>
						{/if}
						<Tabs.Trigger value="related" class="flex-1 gap-1.5">
							Related
							{#if !isLoadingCorrelations && relatedCount > 0}
								<Badge variant="secondary" class="text-[10px] h-5 min-w-5 px-1.5 ml-1">
									{relatedCount}
								</Badge>
							{:else if isLoadingCorrelations}
								<Spinner class="h-3 w-3 text-muted-foreground ml-1" />
							{/if}
						</Tabs.Trigger>
						{#if showDiscoveriesTab}
							<Tabs.Trigger value="discoveries" class="flex-1 gap-1.5">
								Discoveries
								<Sparkles class="h-3 w-3 text-muted-foreground ml-0.5" />
							</Tabs.Trigger>
						{/if}
					</Tabs.List>
				</div>

				{#if scrollHeight > 0}
					<Tabs.Content value="overview">
						<ScrollArea style="height: {scrollHeight}px">
							<div class="px-6 py-5">
								<WhoisOverviewTab
									record={displayRecord}
									onCorrelationClick={handleCorrelationClick}
								/>
							</div>
						</ScrollArea>
					</Tabs.Content>

					{#if hasEntities}
						<Tabs.Content value="entities">
							<ScrollArea style="height: {scrollHeight}px">
								<div class="px-6 py-5">
									<WhoisEntitiesTab record={displayRecord} />
								</div>
							</ScrollArea>
						</Tabs.Content>
					{/if}

					<Tabs.Content value="related">
						<ScrollArea style="height: {scrollHeight}px">
							<div class="px-6 py-5">
								<WhoisRelatedTab
									{correlations}
									isLoading={isLoadingCorrelations}
									error={correlationsError}
									currentRecordId={displayRecord.id}
									onCorrelationClick={handleCorrelationClick}
								/>
							</div>
						</ScrollArea>
					</Tabs.Content>

					{#if showDiscoveriesTab && targetValue && targetType}
						<Tabs.Content value="discoveries">
							<ScrollArea style="height: {scrollHeight}px">
								<div class="px-6 py-5">
									<DiscoveriesSummary
										{targetValue}
										{targetId}
										{targetType}
										whoisRecord={displayRecord}
										{onOpenTargetSummary}
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

<CorrelationLookupDialog
	bind:open={showCorrelationLookup}
	correlationType={correlationLookupType}
	correlationValue={correlationLookupValue}
	onOpenChange={(o) => (showCorrelationLookup = o)}
/>
