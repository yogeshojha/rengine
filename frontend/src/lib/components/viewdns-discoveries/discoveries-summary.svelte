<script lang="ts">
	import PanelSkeleton from '$lib/components/skeleton/panel-skeleton.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { WhoisRecordRead } from '$lib/types/whois';
	import type { ViewDNSCacheRead, DiscoverySourceType } from '$lib/types/viewdns';
	import { DISCOVERY_SOURCE_LABELS, DISCOVERY_SOURCE_DESCRIPTIONS } from '$lib/types/viewdns';
	import { TargetType } from '$lib/types/target';
	import { ADD_TARGETS_BATCH } from '$lib/config/toolbox';
	import { MAX_TARGETS_IMPORT } from '$lib/constants';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Telescope from '@lucide/svelte/icons/telescope';
	import UserRound from '@lucide/svelte/icons/user-round';
	import Server from '@lucide/svelte/icons/server';
	import Globe from '@lucide/svelte/icons/globe';
	import Zap from '@lucide/svelte/icons/zap';
	import Plus from '@lucide/svelte/icons/plus';
	import Check from '@lucide/svelte/icons/check';
	import { Spinner } from '$lib/components/ui/spinner';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { discoveredDomains, planLookups, type Lookup } from './lookups';

	interface Props {
		targetValue: string;
		targetType: TargetType;
		whoisRecord: WhoisRecordRead | null;
	}

	let { targetValue, targetType, whoisRecord }: Props = $props();

	interface SourceResult extends Lookup {
		cache: ViewDNSCacheRead | null;
		domains: string[];
	}

	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let sourceResults = $state<SourceResult[]>([]);

	const adding = new SvelteSet<string>();
	const added = new SvelteMap<string, { duplicate: boolean; targetId: string | null }>();
	const matched = new SvelteMap<string, { valid: boolean; targetId: string | null }>();
	let matchFailed = $state(false);

	let showEnrichDialog = $state(false);
	let enrichSource = $state<DiscoverySourceType | null>(null);
	let enrichQuery = $state('');
	let isEnriching = $state(false);

	const PREVIEW_LIMIT = 15;

	let totalDiscovered = $derived(sourceResults.reduce((sum, s) => sum + s.domains.length, 0));

	let discovered = $derived.by(() => {
		const byKey = new SvelteMap<string, { domain: string; sources: DiscoverySourceType[] }>();
		for (const sr of sourceResults) {
			for (const domain of sr.domains) {
				const key = domain.toLowerCase();
				const row = byKey.get(key);
				if (!row) byKey.set(key, { domain, sources: [sr.source] });
				else if (!row.sources.includes(sr.source)) row.sources.push(sr.source);
			}
		}
		return [...byKey.values()];
	});

	const addable = (domain: string) => {
		const match = matched.get(domain.toLowerCase());
		return match ? match.valid && !match.targetId : matchFailed;
	};
	const isNew = (domain: string) => !added.has(domain.toLowerCase()) && addable(domain);

	let settled = $derived(
		matchFailed || discovered.every((d) => matched.has(d.domain.toLowerCase()))
	);
	let newDomains = $derived(discovered.filter((d) => isNew(d.domain)));
	let previewDomains = $derived(
		[
			...discovered.filter((d) => addable(d.domain)),
			...discovered.filter((d) => !addable(d.domain))
		].slice(0, PREVIEW_LIMIT)
	);
	let pending = $derived(newDomains.map((d) => d.domain));

	let noLookupsAvailable = $derived(planLookups(targetType, targetValue, whoisRecord).length === 0);

	const SOURCE_ICONS: Record<DiscoverySourceType, typeof UserRound> = {
		reverse_whois: UserRound,
		reverse_ip: Server,
		reverse_ns: Globe
	};

	const SOURCE_SHORT: Record<DiscoverySourceType, string> = {
		reverse_whois: 'W',
		reverse_ip: 'IP',
		reverse_ns: 'NS'
	};

	$effect(() => {
		void targetValue;
		void targetType;
		void whoisRecord;
		loadCachedData();
	});

	async function loadCachedData() {
		const lookups = planLookups(targetType, targetValue, whoisRecord);
		if (lookups.length === 0) {
			isLoading = false;
			return;
		}

		isLoading = true;
		error = null;

		try {
			sourceResults = await Promise.all(
				lookups.map(async (lookup): Promise<SourceResult> => {
					try {
						const cache = await lookup.fetch(lookup.queryValue, true);
						const domains = cache ? discoveredDomains(cache, lookup.source, targetValue) : [];
						return { ...lookup, cache, domains };
					} catch {
						return { ...lookup, cache: null, domains: [] };
					}
				})
			);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Discoveries not loaded';
		} finally {
			isLoading = false;
		}
		void matchTargets();
	}

	async function matchTargets() {
		const slug = projectsStore.activeProject?.slug;
		if (!slug) return;
		const domains = [
			...new Set(sourceResults.flatMap((sr) => sr.domains.map((d) => d.toLowerCase())))
		].filter((d) => !matched.has(d));
		for (let i = 0; i < domains.length; i += MAX_TARGETS_IMPORT) {
			const chunk = domains.slice(i, i + MAX_TARGETS_IMPORT);
			try {
				const results = await targetsApi.validateBatch(chunk, slug);
				chunk.forEach((d, j) =>
					matched.set(d, {
						valid: results[j]?.valid ?? false,
						targetId: results[j]?.target_id ?? null
					})
				);
			} catch {
				matchFailed = true;
				return;
			}
		}
	}

	function handleEnrich(source: DiscoverySourceType, queryValue: string) {
		enrichSource = source;
		enrichQuery = queryValue;
		showEnrichDialog = true;
	}

	async function confirmEnrich() {
		const source = enrichSource;
		if (!source) return;
		isEnriching = true;

		try {
			const sr = sourceResults.find((s) => s.source === source && s.queryValue === enrichQuery);
			if (!sr) {
				showEnrichDialog = false;
				return;
			}

			const result = await sr.fetch(enrichQuery, false);
			if (result) {
				const domains = discoveredDomains(result, source, targetValue);

				sourceResults = sourceResults.map((s) =>
					s.source === source && s.queryValue === enrichQuery ? { ...s, cache: result, domains } : s
				);

				toast.success(
					`${plural(domains.length, 'domain')} found via ${DISCOVERY_SOURCE_LABELS[source]}`
				);
				void matchTargets();
			}
			showEnrichDialog = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Lookup not completed');
		} finally {
			isEnriching = false;
		}
	}

	async function addTargets(domains: string[]) {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('Select a project first');
			return;
		}
		if (domains.length === 0) return;

		const one = domains.length === 1 ? domains[0] : null;
		let imported = 0;
		let existing = 0;
		const failures: string[] = [];
		let stopped: string | null = null;
		for (const d of domains) adding.add(d);
		for (let i = 0; i < domains.length; i += ADD_TARGETS_BATCH) {
			try {
				const response = await targetsApi.bulkCreate({
					project_slug: project.slug,
					targets: domains.slice(i, i + ADD_TARGETS_BATCH)
				});
				imported += response.imported;
				existing += response.skipped_duplicates;
				for (const result of response.results) {
					if (result.success || result.duplicate) {
						const key = result.target_value.toLowerCase();
						added.set(key, { duplicate: result.duplicate, targetId: result.target_id });
					} else failures.push(`${result.target_value}: ${result.error ?? 'not added'}`);
				}
			} catch (e) {
				stopped = e instanceof Error ? e.message : 'The API did not respond.';
				break;
			}
		}
		for (const d of domains) adding.delete(d);
		if (imported) void targetsStore.refresh();

		if (stopped) {
			toast.error(
				imported ? `${imported} of ${domains.length} targets added` : 'Targets not added',
				{ description: stopped }
			);
			return;
		}
		if (imported) {
			toast.success(
				one ? `${one} added` : `${imported} ${imported === 1 ? 'target' : 'targets'} added`,
				{
					description: existing ? `${existing} already in this project` : undefined
				}
			);
		} else if (existing) {
			toast.info(one ? `${one} already in this project` : `${existing} already in this project`);
		}
		if (failures.length) {
			toast.warning(one ? `${one} not added` : `${failures.length} not added`, {
				description: failures.slice(0, 3).join('\n')
			});
		}
	}
</script>

{#if isLoading}
	<PanelSkeleton stats rows={5} />
{:else if error}
	<EmptyState compact icon={TriangleAlert} title="Discoveries not loaded" description={error}>
		<Button size="sm" variant="outline" onclick={() => loadCachedData()}>Retry</Button>
	</EmptyState>
{:else if noLookupsAvailable}
	<EmptyState
		compact
		icon={Telescope}
		title="No discoveries"
		description="The WHOIS record has no registrant or nameserver."
	/>
{:else}
	<div class="space-y-5 py-1">
		{#if totalDiscovered > 0}
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<span>
					<span class="font-semibold text-foreground">{totalDiscovered.toLocaleString()}</span>
					discovered {totalDiscovered === 1 ? 'domain' : 'domains'}
					across {sourceResults.filter((s) => s.cache).length}
					{sourceResults.filter((s) => s.cache).length === 1 ? 'source' : 'sources'}
					{#if settled && !matchFailed}
						· <span class="font-medium text-foreground">{newDomains.length.toLocaleString()}</span>
						new
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
										<Badge variant="outline" class="text-2xs h-5 px-1.5 font-normal">
											{sr.domains.length.toLocaleString()} domains
										</Badge>
										{#if settled && !matchFailed}
											{@const fresh = sr.domains.filter(isNew).length}
											{#if fresh > 0}
												<Badge variant="outline" class="text-2xs h-5 px-1.5 font-normal">
													{fresh.toLocaleString()} new
												</Badge>
											{/if}
										{/if}
									{/if}
								</div>
								<p class="text-2xs text-muted-foreground truncate mt-0.5">
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
				<SectionHead title="Domains" />
				<div class="rounded-lg border border-border/60 divide-y divide-border/30">
					{#each previewDomains as { domain, sources } (domain)}
						{@const isAdding = adding.has(domain)}
						{@const done = added.get(domain.toLowerCase())}
						{@const targetId = done?.targetId ?? matched.get(domain.toLowerCase())?.targetId}
						<div class="flex items-center justify-between gap-3 px-3 py-1.5 group">
							<div class="flex items-center gap-2 min-w-0">
								<span class="text-sm font-mono truncate">{domain}</span>
								{#each sources as source (source)}
									<Hint text="Found via {DISCOVERY_SOURCE_LABELS[source]}">
										{#snippet child(props)}
											<Badge
												{...props}
												variant="outline"
												class="text-2xs font-normal shrink-0 h-4 px-1 text-muted-foreground border-border/60 cursor-default"
											>
												{SOURCE_SHORT[source]}
											</Badge>
										{/snippet}
									</Hint>
								{/each}
							</div>
							<div class="flex h-7 shrink-0 items-center">
								{#if targetId}
									<a
										href={ROUTES.target(targetId)}
										class="flex items-center gap-1 text-2xs text-muted-foreground hover:text-foreground"
									>
										<Check class="h-3 w-3" />
										{done && !done.duplicate ? 'Added' : 'Target'}
									</a>
								{:else if done}
									<span class="flex items-center gap-1 text-2xs text-muted-foreground">
										<Check class="h-3 w-3" />
										Added
									</span>
								{:else if isAdding}
									<Spinner class="h-3.5 w-3.5 text-muted-foreground" />
								{:else if isNew(domain)}
									<Hint text="Add as target">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
												aria-label="Add {domain} as target"
												onclick={() => addTargets([domain])}
											>
												<Plus class="h-3 w-3" />
											</Button>
										{/snippet}
									</Hint>
								{/if}
							</div>
						</div>
					{/each}
				</div>
				{#if discovered.length > PREVIEW_LIMIT}
					<p class="text-2xs text-muted-foreground text-center">
						and {(discovered.length - PREVIEW_LIMIT).toLocaleString()} more
					</p>
				{/if}
			</div>
		{/if}

		{#if settled && pending.length > 0}
			<Button
				variant="outline"
				class="w-full gap-2 text-sm"
				disabled={adding.size > 0}
				onclick={() => addTargets(pending)}
			>
				<Plus class="h-4 w-4" />
				Add {pending.length.toLocaleString()}
				{pending.length === 1 ? 'domain as a target' : 'domains as targets'}
			</Button>
		{/if}

		{#if sourceResults.some((s) => s.cache)}
			<p class="text-2xs text-muted-foreground/60 text-center">ViewDNS.info · cached data</p>
		{/if}
	</div>
{/if}

<ConfirmDialog
	open={showEnrichDialog}
	title={`Enrich ${enrichSource ? DISCOVERY_SOURCE_LABELS[enrichSource] : 'ViewDNS'}`}
	description={`Queries ViewDNS.info for ${enrichQuery} and uses 1 API credit. Results are cached for 7 days.`}
	confirmLabel="Enrich"
	loading={isEnriching}
	loadingLabel="Enriching"
	onOpenChange={(o) => (showEnrichDialog = o)}
	onConfirm={confirmEnrich}
/>
