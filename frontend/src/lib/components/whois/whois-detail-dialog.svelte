<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { whoisApi } from '$lib/api/whois';
	import {
		whoisLookupLabel,
		type WhoisRecordRead,
		type WhoisCorrelationResult
	} from '$lib/types/whois';
	import { TargetType } from '$lib/types/target';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tabs from '$lib/components/ui/tabs';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { toast } from 'svelte-sonner';
	import WhoisOverviewTab from './whois-overview-tab.svelte';
	import WhoisEntitiesTab from './whois-entities-tab.svelte';
	import WhoisRelatedTab from './whois-related-tab.svelte';
	import CorrelationLookupDialog from './correlation-lookup-dialog.svelte';
	import DiscoveriesSummary from '$lib/components/viewdns-discoveries/discoveries-summary.svelte';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import FileSearch from '@lucide/svelte/icons/file-search';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getLookupTypeIcon } from '$lib/config/icons';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
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

	const SCROLL = 'min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-12rem)]';

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
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="border-b px-6 py-4 pr-12">
			<div class="flex items-center gap-3">
				<div
					class="flex size-10 shrink-0 items-center justify-center rounded-lg border bg-muted/40"
				>
					<LookupIcon class="size-5 text-muted-foreground" />
				</div>
				<div class="flex min-w-0 flex-1 flex-col gap-1">
					<Dialog.Title class="truncate font-mono">
						{#if displayRecord}
							{displayRecord.name || displayRecord.query_value}
						{:else if isLoadingRecord && targetValue}
							{targetValue}
						{:else if isLoadingRecord}
							<Skeleton class="h-5 w-48" />
						{:else}
							{targetValue ?? 'WHOIS record'}
						{/if}
					</Dialog.Title>
					<Dialog.Description>WHOIS / RDAP record</Dialog.Description>
				</div>
			</div>
		</Dialog.Header>

		{#if isLoadingRecord && !displayRecord}
			<div class="flex flex-col gap-5 px-6 py-5" aria-busy="true">
				<div class="flex h-7 items-center justify-between gap-4">
					<Skeleton class="h-4 w-40" />
					<Skeleton class="h-4 w-28" />
				</div>
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
			<div class="px-6 py-5">
				<EmptyState
					compact
					icon={TriangleAlert}
					title="WHOIS record not loaded"
					description={recordError}
				>
					<Button size="sm" variant="outline" onclick={() => loadData()}>Retry</Button>
				</EmptyState>
			</div>
		{:else if displayRecord}
			<div class="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 px-6 pt-5">
				<div class="flex min-w-0 items-center gap-1.5">
					<span class="text-sm">
						<span class="font-medium">{whoisLookupLabel(displayRecord.lookup_type)}</span>
						{#if displayRecord.handle}
							<span class="text-muted-foreground">·</span>
							<span class="font-mono text-xs text-muted-foreground">{displayRecord.handle}</span>
						{/if}
					</span>
					<CopyButton value={displayRecord.query_value} label="Copy {displayRecord.query_value}" />
				</div>
				<div class="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
					<Hint text="Last refreshed {formatDateTime(displayRecord.queried_at)}">
						{#snippet child(props)}
							<span {...props} class="tabular-nums">
								queried {relativeTime(displayRecord?.queried_at)}
							</span>
						{/snippet}
					</Hint>
					<Button
						variant="ghost"
						size="icon"
						class="size-7 text-muted-foreground hover:text-foreground"
						disabled={isRefreshing}
						aria-label="Refresh WHOIS record"
						onclick={handleRefresh}
					>
						<RefreshCw class="size-3.5 {isRefreshing ? 'animate-spin' : ''}" />
					</Button>
				</div>
			</div>

			<Tabs.Root bind:value={activeTab} class="flex min-h-0 flex-1 flex-col">
				<div class="shrink-0 border-b px-6 pt-3">
					<ScrollArea orientation="horizontal" class="w-full">
						<Tabs.List variant="line" class="w-max justify-start">
							<Tabs.Trigger value="overview" class="flex-none px-3">Overview</Tabs.Trigger>
							{#if hasEntities}
								<Tabs.Trigger value="entities" class="flex-none px-3">Entities</Tabs.Trigger>
							{/if}
							<Tabs.Trigger value="related" class="flex-none px-3">
								Related
								{#if !isLoadingCorrelations && relatedCount > 0}
									<span class="text-xs text-muted-foreground tabular-nums">{relatedCount}</span>
								{:else if isLoadingCorrelations}
									<Spinner class="size-3 text-muted-foreground" />
								{/if}
							</Tabs.Trigger>
							{#if showDiscoveriesTab}
								<Tabs.Trigger value="discoveries" class="flex-none px-3">Discoveries</Tabs.Trigger>
							{/if}
						</Tabs.List>
					</ScrollArea>
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
								onRetry={loadCorrelations}
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
		{:else if !recordId}
			<div class="px-6 py-5">
				<EmptyState compact icon={FileSearch} title="No WHOIS record" />
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<CorrelationLookupDialog
	bind:open={showCorrelationLookup}
	correlationType={correlationLookupType}
	correlationValue={correlationLookupValue}
	onOpenChange={(o) => (showCorrelationLookup = o)}
/>
