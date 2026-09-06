<script lang="ts">
	import { viewdnsApi } from '$lib/api/viewdns';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { WhoisRecordRead } from '$lib/types/whois';
	import type {
		ViewDNSCacheRead,
		DiscoverySourceType,
		ReverseWhoisResponse,
		ReverseIPResponse,
		ReverseNSResponse
	} from '$lib/types/viewdns';
	import { DISCOVERY_SOURCE_LABELS, DISCOVERY_SOURCE_DESCRIPTIONS } from '$lib/types/viewdns';
	import { TargetType } from '$lib/types/target';
	import { relativeTime } from '$lib/utilities/dates';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import EnrichConfirmDialog from './enrich-confirm-dialog.svelte';
	import { toast } from 'svelte-sonner';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Telescope from '@lucide/svelte/icons/telescope';
	import UserRound from '@lucide/svelte/icons/user-round';
	import Server from '@lucide/svelte/icons/server';
	import Globe from '@lucide/svelte/icons/globe';
	import Zap from '@lucide/svelte/icons/zap';
	import Plus from '@lucide/svelte/icons/plus';
	import Check from '@lucide/svelte/icons/check';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { Spinner } from '$lib/components/ui/spinner';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		targetValue: string;
		targetId: string;
		targetType: TargetType;
		whoisRecord: WhoisRecordRead | null;
		onOpenTargetSummary?: () => void;
	}

	let { targetValue, targetId, targetType, whoisRecord, onOpenTargetSummary }: Props = $props();

	interface SourceResult {
		source: DiscoverySourceType;
		queryValue: string;
		cache: ViewDNSCacheRead | null;
		domains: string[];
		newDomains: string[];
		fetch: (q: string, cachedOnly: boolean) => Promise<ViewDNSCacheRead | null>;
	}

	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let sourceResults = $state<SourceResult[]>([]);

	let addingDomains = $state(new Set<string>());
	let addedDomains = $state(new Set<string>());

	let showEnrichDialog = $state(false);
	let enrichSource = $state<DiscoverySourceType | null>(null);
	let enrichQuery = $state('');
	let isEnriching = $state(false);

	const PREVIEW_LIMIT = 15;

	let existingTargetValues = $derived(
		new Set(targetsStore.targets.map((t) => t.target_value.toLowerCase()))
	);

	let totalDiscovered = $derived(sourceResults.reduce((sum, s) => sum + s.domains.length, 0));

	let totalNew = $derived(sourceResults.reduce((sum, s) => sum + s.newDomains.length, 0));

	let previewDomains = $derived.by(() => {
		const seen = new SvelteSet<string>();
		const result: { domain: string; sources: DiscoverySourceType[] }[] = [];

		for (const sr of sourceResults) {
			for (const domain of sr.newDomains) {
				const key = domain.toLowerCase();
				if (seen.has(key)) {
					const existing = result.find((r) => r.domain.toLowerCase() === key);
					if (existing && !existing.sources.includes(sr.source)) {
						existing.sources.push(sr.source);
					}
					continue;
				}
				seen.add(key);
				result.push({ domain, sources: [sr.source] });
				if (result.length >= PREVIEW_LIMIT) return result;
			}
		}
		return result;
	});

	let noLookupsAvailable = $derived(planLookups().length === 0);

	const SOURCE_ICONS: Record<DiscoverySourceType, typeof UserRound> = {
		reverse_whois: UserRound,
		reverse_ip: Server,
		reverse_ns: Globe
	};

	function planLookups(): {
		source: DiscoverySourceType;
		queryValue: string;
		fetch: (q: string, cachedOnly: boolean) => Promise<ViewDNSCacheRead | null>;
	}[] {
		const lookups: ReturnType<typeof planLookups> = [];

		if (targetType === TargetType.DOMAIN) {
			if (whoisRecord?.registrant_name) {
				lookups.push({
					source: 'reverse_whois',
					queryValue: whoisRecord.registrant_name,
					fetch: viewdnsApi.reverseWhois
				});
			} else if (whoisRecord?.registrant_email) {
				lookups.push({
					source: 'reverse_whois',
					queryValue: whoisRecord.registrant_email,
					fetch: viewdnsApi.reverseWhois
				});
			}

			const nameservers = whoisRecord?.nameservers as string[] | null;
			if (nameservers?.length) {
				const ns = nameservers[0];
				if (ns) {
					lookups.push({
						source: 'reverse_ns',
						queryValue: ns,
						fetch: viewdnsApi.reverseNs
					});
				}
			}
		} else if (targetType === TargetType.IP) {
			lookups.push({
				source: 'reverse_ip',
				queryValue: targetValue,
				fetch: viewdnsApi.reverseIp
			});
		}

		return lookups;
	}

	$effect(() => {
		void targetValue;
		void targetType;
		void whoisRecord;
		loadCachedData();
	});

	async function loadCachedData() {
		const lookups = planLookups();
		if (lookups.length === 0) {
			isLoading = false;
			return;
		}

		isLoading = true;
		error = null;

		try {
			const results = await Promise.all(
				lookups.map(async (lookup) => {
					try {
						const cache = await lookup.fetch(lookup.queryValue, true);
						const domains = cache ? extractDomains(cache, lookup.source) : [];
						const filtered = domains.filter((d) => d.toLowerCase() !== targetValue.toLowerCase());
						const newDomains = filtered.filter(
							(d) =>
								!existingTargetValues.has(d.toLowerCase()) && !addedDomains.has(d.toLowerCase())
						);

						return {
							source: lookup.source,
							queryValue: lookup.queryValue,
							cache,
							domains: filtered,
							newDomains,
							fetch: lookup.fetch
						} as SourceResult;
					} catch {
						return {
							source: lookup.source,
							queryValue: lookup.queryValue,
							cache: null,
							domains: [],
							newDomains: [],
							fetch: lookup.fetch
						} as SourceResult;
					}
				})
			);

			sourceResults = results;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Discoveries could not be loaded';
		} finally {
			isLoading = false;
		}
	}

	function extractDomains(cache: ViewDNSCacheRead, source: DiscoverySourceType): string[] {
		const data = cache.data;
		switch (source) {
			case 'reverse_whois':
				return (data as ReverseWhoisResponse).matches?.map((m) => m.domain).filter(Boolean) ?? [];
			case 'reverse_ip':
				return (data as ReverseIPResponse).domains?.map((m) => m.name).filter(Boolean) ?? [];
			case 'reverse_ns':
				return (data as ReverseNSResponse).domains?.map((m) => m.domain).filter(Boolean) ?? [];
			default:
				return [];
		}
	}

	function handleEnrich(source: DiscoverySourceType, queryValue: string) {
		enrichSource = source;
		enrichQuery = queryValue;
		showEnrichDialog = true;
	}

	async function confirmEnrich() {
		if (!enrichSource) return;
		isEnriching = true;

		try {
			const sr = sourceResults.find(
				(s) => s.source === enrichSource && s.queryValue === enrichQuery
			);
			if (!sr) return;

			const result = await sr.fetch(enrichQuery, false);
			if (result) {
				const domains = extractDomains(result, sr.source);
				const filtered = domains.filter((d) => d.toLowerCase() !== targetValue.toLowerCase());
				const newDomains = filtered.filter(
					(d) => !existingTargetValues.has(d.toLowerCase()) && !addedDomains.has(d.toLowerCase())
				);

				sourceResults = sourceResults.map((s) =>
					s.source === enrichSource && s.queryValue === enrichQuery
						? { ...s, cache: result, domains: filtered, newDomains }
						: s
				);

				toast.success(
					`Found ${filtered.length} domains via ${DISCOVERY_SOURCE_LABELS[enrichSource!]}`
				);
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Enrichment failed');
		} finally {
			isEnriching = false;
			showEnrichDialog = false;
		}
	}

	async function handleAddTarget(domain: string) {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug) {
			toast.error('Select a project first');
			return;
		}

		addingDomains = new Set([...addingDomains, domain]);

		try {
			const result = await targetsStore.createTarget({
				target_value: domain,
				project_slug: projectSlug
			});
			if (result) {
				addedDomains = new Set([...addedDomains, domain.toLowerCase()]);
				toast.success(`Added ${domain} as target`);
			}
		} catch {
			toast.error(`${domain} could not be added`);
		} finally {
			const next = new SvelteSet(addingDomains);
			next.delete(domain);
			addingDomains = next;
		}
	}

	async function handleAddAllNew() {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug) {
			toast.error('Select a project first');
			return;
		}

		const allNew = new SvelteSet<string>();
		for (const sr of sourceResults) {
			for (const d of sr.newDomains) {
				if (!addedDomains.has(d.toLowerCase())) {
					allNew.add(d);
				}
			}
		}

		if (allNew.size === 0) return;

		const total = allNew.size;
		let added = 0;
		for (const domain of allNew) {
			addingDomains = new Set([...addingDomains, domain]);
			try {
				const result = await targetsStore.createTarget({
					target_value: domain,
					project_slug: projectSlug
				});
				if (result) {
					addedDomains = new Set([...addedDomains, domain.toLowerCase()]);
					added++;
				}
			} catch {
			} finally {
				const next = new SvelteSet(addingDomains);
				next.delete(domain);
				addingDomains = next;
			}
		}

		const failed = total - added;
		if (added === total) {
			toast.success(`Added ${added} target${added !== 1 ? 's' : ''}`);
		} else if (added > 0) {
			toast.warning(`Added ${added} of ${total}; ${failed} failed`);
		} else {
			toast.error(
				'Domains could not be added. They may already exist, or the ViewDNS quota is exhausted.'
			);
		}
	}

	function handleOpenTargetSummary() {
		if (onOpenTargetSummary) onOpenTargetSummary();
		else goto(ROUTES.target(targetId));
	}
</script>

{#if isLoading}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Spinner />
			</Empty.Media>
			<Empty.Title>Loading discoveries…</Empty.Title>
			<Empty.Description>Checking cached ViewDNS intelligence.</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if error}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<SearchX />
			</Empty.Media>
			<Empty.Title>Discoveries could not be loaded</Empty.Title>
			<Empty.Description>{error}</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if noLookupsAvailable}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Telescope />
			</Empty.Media>
			<Empty.Title>Discoveries not available</Empty.Title>
			<Empty.Description>
				{#if targetType === TargetType.DOMAIN && !whoisRecord}
					WHOIS data is needed to find related domains. Discoveries will appear once WHOIS resolves
					with registrant and nameserver data.
				{:else}
					Discoveries are available for domain and IP targets.
				{/if}
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-5 py-1">
		{#if totalDiscovered > 0}
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<Sparkles class="h-4 w-4 text-muted-foreground" />
				<span>
					<span class="font-semibold text-foreground">{totalDiscovered.toLocaleString()}</span>
					discovered {totalDiscovered === 1 ? 'domain' : 'domains'}
					across {sourceResults.filter((s) => s.cache).length}
					{sourceResults.filter((s) => s.cache).length === 1 ? 'source' : 'sources'}
					{#if totalNew > 0}
						·
						<span class="text-primary font-medium">{totalNew.toLocaleString()} new</span>
					{/if}
				</span>
			</div>
		{/if}

		<div class="space-y-2">
			{#each sourceResults as sr (sr.source + ':' + sr.queryValue)}
				{@const Icon = SOURCE_ICONS[sr.source]}
				<div class="rounded-lg border border-border/60 p-3">
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-2.5 min-w-0">
							<div class="flex items-center justify-center h-8 w-8 rounded-md shrink-0 bg-muted/60">
								<Icon class="h-4 w-4 text-muted-foreground" />
							</div>
							<div class="min-w-0">
								<div class="flex items-center gap-2">
									<span class="text-sm font-medium">
										{DISCOVERY_SOURCE_LABELS[sr.source]}
									</span>
									{#if sr.cache}
										<Badge variant="outline" class="text-[10px] h-5 px-1.5 font-normal">
											{sr.domains.length.toLocaleString()} domains
										</Badge>
										{#if sr.newDomains.length > 0}
											<Badge
												variant="outline"
												class="text-[10px] h-5 px-1.5 font-normal text-chart-1 border-chart-1/30"
											>
												{sr.newDomains.length.toLocaleString()} new
											</Badge>
										{/if}
									{/if}
								</div>
								<p class="text-[11px] text-muted-foreground truncate mt-0.5">
									{#if sr.cache}
										via <span class="font-mono">{sr.queryValue}</span>
										{#if sr.cache.queried_at}
											· fetched {relativeTime(sr.cache.queried_at)}
										{/if}
									{:else}
										{DISCOVERY_SOURCE_DESCRIPTIONS[sr.source]}
									{/if}
								</p>
							</div>
						</div>

						{#if !sr.cache}
							<Button
								variant="outline"
								size="sm"
								class="gap-1.5 text-xs h-7 shrink-0"
								onclick={() => handleEnrich(sr.source, sr.queryValue)}
							>
								<Zap class="h-3 w-3" />
								Enrich
							</Button>
						{/if}
					</div>
				</div>
			{/each}
		</div>

		{#if previewDomains.length > 0}
			<div class="space-y-2">
				<p class="text-xs font-medium text-muted-foreground uppercase tracking-wider">
					New domains preview
				</p>
				<div class="rounded-lg border border-border/60 divide-y divide-border/30">
					{#each previewDomains as { domain, sources } (domain)}
						{@const isAdding = addingDomains.has(domain)}
						{@const isAdded = addedDomains.has(domain.toLowerCase())}
						<div class="flex items-center justify-between gap-3 px-3 py-2 group">
							<div class="flex items-center gap-2 min-w-0">
								<span class="text-sm font-mono truncate">{domain}</span>
								{#each sources as source (source)}
									<Tooltip.Root>
										<Tooltip.Trigger>
											{#snippet child({ props })}
												<Badge
													{...props}
													variant="outline"
													class="text-[10px] font-normal shrink-0 h-4 px-1 text-muted-foreground border-border/60 cursor-default"
												>
													{source === 'reverse_whois' ? 'W' : source === 'reverse_ip' ? 'IP' : 'NS'}
												</Badge>
											{/snippet}
										</Tooltip.Trigger>
										<Tooltip.Content>Found via {DISCOVERY_SOURCE_LABELS[source]}</Tooltip.Content>
									</Tooltip.Root>
								{/each}
							</div>
							<div class="shrink-0">
								{#if isAdded}
									<span class="flex items-center gap-1 text-[11px] text-muted-foreground">
										<Check class="h-3 w-3" />
										Added
									</span>
								{:else if isAdding}
									<Spinner class="h-3.5 w-3.5 text-muted-foreground" />
								{:else}
									<Tooltip.Root>
										<Tooltip.Trigger>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="icon"
													class="h-6 w-6 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
													onclick={() => handleAddTarget(domain)}
												>
													<Plus class="h-3 w-3" />
												</Button>
											{/snippet}
										</Tooltip.Trigger>
										<Tooltip.Content>Add as target</Tooltip.Content>
									</Tooltip.Root>
								{/if}
							</div>
						</div>
					{/each}
				</div>
				{#if totalNew > PREVIEW_LIMIT}
					<p class="text-[11px] text-muted-foreground text-center">
						and {(totalNew - PREVIEW_LIMIT).toLocaleString()} more new domains
					</p>
				{/if}
			</div>
		{/if}

		{#if totalNew > 0}
			<Button variant="outline" class="w-full gap-2 text-sm" onclick={handleAddAllNew}>
				<Plus class="h-4 w-4" />
				Add all {totalNew.toLocaleString()} new domains as targets
			</Button>
		{/if}

		<button
			type="button"
			class="w-full rounded-lg border border-dashed border-border/50 bg-muted/20 px-4 py-3 text-left hover:bg-muted/40 hover:border-border transition-colors group cursor-pointer"
			onclick={handleOpenTargetSummary}
		>
			<div class="flex items-start gap-2.5">
				<ArrowRight
					class="h-4 w-4 text-muted-foreground mt-0.5 shrink-0 group-hover:text-primary transition-colors"
				/>
				<div>
					<p class="text-xs font-medium text-foreground group-hover:text-primary transition-colors">
						View all in Target Summary
					</p>
					<p class="text-[11px] text-muted-foreground mt-0.5">
						Search, filter, and bulk-add from {totalDiscovered > 0
							? totalDiscovered.toLocaleString() + '+'
							: 'all'} discovered domains with full pagination.
					</p>
				</div>
			</div>
		</button>

		{#if sourceResults.some((s) => s.cache)}
			<p class="text-[11px] text-muted-foreground/60 text-center">
				Powered by ViewDNS.info · Showing cached data
			</p>
		{/if}
	</div>
{/if}

<EnrichConfirmDialog
	bind:open={showEnrichDialog}
	source={enrichSource}
	queryValue={enrichQuery}
	{isEnriching}
	onOpenChange={(o) => (showEnrichDialog = o)}
	onConfirm={confirmEnrich}
/>
