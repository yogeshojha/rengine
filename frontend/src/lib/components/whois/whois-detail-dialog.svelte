<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { whoisApi } from '$lib/api/whois';
	import type { WhoisRecordRead, WhoisCorrelationResult } from '$lib/types/whois';
	import { TargetType } from '$lib/types/target';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Empty from '$lib/components/ui/empty';
	import Hint from '$lib/components/hint.svelte';
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
	import { Spinner } from '$lib/components/ui/spinner';
	import { getLookupTypeIcon } from '$lib/config/icons';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		open: boolean;
		recordId?: string | null;
		targetId?: string;
		targetValue?: string | null;
		targetType?: TargetType | null;
		initialTab?: string;
		onOpenChange: (open: boolean) => void;
	}

	let {
		open = $bindable(),
		recordId = null,
		targetId,
		targetValue = null,
		targetType = null,
		initialTab = 'overview',
		onOpenChange
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

	let displayRecord = $derived(internalRecord);

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

	let discoveries = $derived(
		targetValue && targetId && (targetType === TargetType.DOMAIN || targetType === TargetType.IP)
			? { value: targetValue, type: targetType }
			: null
	);
	let showDiscoveriesTab = $derived(discoveries !== null);

	const SCROLL = 'min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-9rem)]';

	$effect(() => {
		if (open) {
			activeTab = initialTab;
			loadData();
		} else {
			internalRecord = null;
			correlations = [];
			recordError = null;
			correlationsError = null;
		}
	});

	async function loadCorrelations() {
		if (!targetId) return;
		isLoadingCorrelations = true;
		correlationsError = null;
		try {
			correlations = await whoisApi.getTargetCorrelations(targetId);
		} catch (e) {
			correlationsError = e instanceof Error ? e.message : 'Correlations not loaded';
		} finally {
			isLoadingCorrelations = false;
		}
	}

	async function loadData() {
		if (recordId) {
			isLoadingRecord = true;
			recordError = null;
			try {
				internalRecord = await whoisApi.getRecord(recordId);
			} catch (e) {
				recordError = e instanceof Error ? e.message : 'WHOIS record not loaded';
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
			toast.error(e instanceof Error ? e.message : 'WHOIS record not refreshed');
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
		<div class="shrink-0">
			<Dialog.Header class="px-6 pt-6 pb-4">
				<div class="flex items-center gap-3">
					<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-muted shrink-0">
						{#if isLoadingRecord}
							<Spinner class="h-5 w-5 text-muted-foreground" />
						{:else}
							<LookupIcon class="h-5 w-5 text-muted-foreground" />
						{/if}
					</div>
					<div class="min-w-0 flex-1">
						<Dialog.Title class="text-lg font-semibold truncate">
							{#if displayRecord}
								{displayRecord.name || displayRecord.query_value}
							{:else if isLoadingRecord && targetValue}
								{targetValue}
							{:else if isLoadingRecord}
								<Skeleton class="h-5 w-48" />
							{:else}
								WHOIS record
							{/if}
						</Dialog.Title>
						<Dialog.Description class="text-sm text-muted-foreground">
							WHOIS / RDAP record
						</Dialog.Description>
					</div>
					{#if displayRecord}
						<Hint text="Refresh WHOIS record">
							{#snippet child(props)}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="h-8 w-8 shrink-0"
									aria-label="Refresh"
									onclick={handleRefresh}
									disabled={isRefreshing}
								>
									<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
								</Button>
							{/snippet}
						</Hint>
					{/if}
				</div>
			</Dialog.Header>
		</div>

		{#if isLoadingRecord && !displayRecord}
			<div class="flex flex-col gap-5 px-6 py-5" aria-busy="true">
				<div class="flex gap-2">
					{#each Array(3) as _, i (i)}
						<Skeleton class="h-9 flex-1" />
					{/each}
				</div>
				{#each Array(6) as _, i (i)}
					<div class="flex flex-col gap-2">
						<Skeleton class="h-3 w-24" />
						<Skeleton class="h-4 {i % 2 ? 'w-2/3' : 'w-1/2'}" />
					</div>
				{/each}
			</div>
		{:else if recordError}
			<Empty.Root>
				<Empty.Header>
					<Empty.Media variant="icon">
						<TriangleAlert />
					</Empty.Media>
					<Empty.Title>WHOIS record not loaded</Empty.Title>
					<Empty.Description>{recordError}</Empty.Description>
				</Empty.Header>
			</Empty.Root>
		{:else if displayRecord}
			<Tabs.Root bind:value={activeTab} class="flex min-h-0 flex-1 flex-col">
				<div class="px-6 shrink-0">
					<Tabs.List class="w-full">
						<Tabs.Trigger value="overview" class="flex-1">Overview</Tabs.Trigger>
						{#if hasEntities}
							<Tabs.Trigger value="entities" class="flex-1">Entities</Tabs.Trigger>
						{/if}
						<Tabs.Trigger value="related" class="flex-1 gap-1.5">
							Related
							{#if !isLoadingCorrelations && relatedCount > 0}
								<Badge variant="secondary" class="text-2xs h-5 min-w-5 px-1.5 ml-1">
									{relatedCount}
								</Badge>
							{:else if isLoadingCorrelations}
								<Spinner class="h-3 w-3 text-muted-foreground ml-1" />
							{/if}
						</Tabs.Trigger>
						{#if showDiscoveriesTab}
							<Tabs.Trigger value="discoveries" class="flex-1 gap-1.5">Discoveries</Tabs.Trigger>
						{/if}
					</Tabs.List>
				</div>

				<Tabs.Content value="overview" class="flex min-h-0 flex-1 flex-col">
					<ScrollArea class={SCROLL}>
						<div class="px-6 py-5">
							<WhoisOverviewTab
								record={displayRecord}
								onCorrelationClick={handleCorrelationClick}
							/>
						</div>
					</ScrollArea>
				</Tabs.Content>

				{#if hasEntities}
					<Tabs.Content value="entities" class="flex min-h-0 flex-1 flex-col">
						<ScrollArea class={SCROLL}>
							<div class="px-6 py-5">
								<WhoisEntitiesTab record={displayRecord} />
							</div>
						</ScrollArea>
					</Tabs.Content>
				{/if}

				<Tabs.Content value="related" class="flex min-h-0 flex-1 flex-col">
					<ScrollArea class={SCROLL}>
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

				{#if discoveries}
					<Tabs.Content value="discoveries" class="flex min-h-0 flex-1 flex-col">
						<ScrollArea class={SCROLL}>
							<div class="px-6 py-5">
								<DiscoveriesSummary
									targetValue={discoveries.value}
									targetType={discoveries.type}
									whoisRecord={displayRecord}
								/>
							</div>
						</ScrollArea>
					</Tabs.Content>
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
