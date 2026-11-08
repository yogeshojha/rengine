<script lang="ts">
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { onDestroy, untrack } from 'svelte';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import { Button } from '$lib/components/ui/button';
	import EmptyState from '$lib/components/empty-state.svelte';
	import HeroPanel from './overview/hero-panel.svelte';
	import AttentionPanel from './overview/attention-panel.svelte';
	import PosturePanel from './overview/posture-panel.svelte';
	import CompositionPanel from './overview/composition-panel.svelte';
	import ExposurePanel from './overview/exposure-panel.svelte';
	import StructurePanel from './overview/structure-panel.svelte';
	import VulnerabilityPanel from './overview/vulnerability-panel.svelte';
	import HostingPanel from './overview/hosting-panel.svelte';
	import HygienePanel from './overview/hygiene-panel.svelte';
	import DomainPosturePanel from './overview/domain-posture-panel.svelte';
	import EstateTray from '$lib/components/targets/estate-tray.svelte';
	import LookalikeTray from '$lib/components/lookalikes/lookalike-tray.svelte';
	import { lookalikesApi } from '$lib/api/lookalikes';
	import type { LookalikeSummary } from '$lib/types/lookalike';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { targetsApi } from '$lib/api/targets';
	import { domainPostureApi } from '$lib/api/domain-posture';
	import { endpointsApi, servicesApi } from '$lib/api/scan-results';
	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import { LiveRefresh, LIVE_OVERVIEW_MS } from '$lib/utilities/live-results';
	import { targetAssetNoun, TargetType } from '$lib/types/target';
	import { scanFoundNothing } from '$lib/types/scan';
	import type { ScanActivityRead, ScanRead } from '$lib/types/scan';
	import type { HygieneSummary, SubdomainInsights } from '$lib/utilities/scan-insights';
	import type { ScanExposure } from '$lib/utilities/services';
	import type { ScanStructure } from '$lib/utilities/endpoints';
	import type { ScanVulnerabilities } from '$lib/utilities/vulns';
	import type { OriginExposure } from '$lib/utilities/origins';
	import type { HostingComposition } from '$lib/types/hosting';
	import type { DomainPostureSummary } from '$lib/types/domain-posture';
	import type { TargetEstate } from '$lib/types/estate';

	interface Props {
		scan: ScanRead;
		scanId: string;
		projectId: string;
		activities: ScanActivityRead[];
		history: ScanRead[];
		historyLoaded: boolean;
		previous: ScanRead | null;
		previousDuration: number | null;
		now: number;
		active?: boolean;
		revision?: number;
		onFilter: (search: string) => void;
		onTab: (tab: ResultTab, filter?: string) => void;
		onRescan: () => void;
	}

	let {
		scan,
		scanId,
		projectId,
		activities,
		history,
		historyLoaded,
		previous,
		previousDuration,
		now,
		active = true,
		revision = 0,
		onFilter,
		onTab,
		onRescan
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let insights = $state<SubdomainInsights | null>(null);
	let estate = $state<TargetEstate | null>(null);
	let exposure = $state<ScanExposure | null>(null);
	let structure = $state<ScanStructure | null>(null);
	let vulns = $state<ScanVulnerabilities | null>(null);
	let origins = $state<OriginExposure | null>(null);
	let loading = $state(true);
	let errored = $state(false);

	let live = $derived(isLiveStatus(scan.status));
	let run = $derived(live ? liveScans.runFor(scan.id) : undefined);
	let catalog = $derived(engineCatalogStore.stages);
	let type = $derived(scan.execution_config.target_type);
	const nounPlural = targetAssetNoun();
	let isDomain = $derived(type === TargetType.DOMAIN);
	let signature = $derived([scanId, projectId, scan.status].join(':'));

	let generation = 0;

	function into<T>(mine: number, request: Promise<T>, apply: (value: T | null) => void) {
		return request.then(
			(value) => {
				if (mine === generation) apply(value);
			},
			() => {
				if (mine === generation) apply(null);
			}
		);
	}

	function loadInsights(mine: number) {
		if (!insights) loading = true;
		errored = false;
		return subdomainsApi
			.insights(projectId, scanId)
			.then((d) => {
				if (mine !== generation) return;
				insights = d;
				errored = false;
			})
			.catch(() => {
				if (mine === generation && !insights) errored = true;
			})
			.finally(() => {
				if (mine === generation) loading = false;
			});
	}

	const loadExposure = (mine: number) =>
		into(mine, servicesApi.exposure(projectId, scanId), (d) => (exposure = d));
	const loadStructure = (mine: number) =>
		into(mine, endpointsApi.structure(projectId, scanId), (d) => (structure = d));
	const loadVulns = (mine: number) =>
		into(mine, vulnerabilitiesApi.overview(projectId, scanId), (d) => (vulns = d));
	const loadOrigins = (mine: number) =>
		into(mine, servicesApi.origins(projectId, scanId), (d) => (origins = d));

	let hygiene = $state<HygieneSummary | null>(null);
	const loadHygiene = (mine: number) =>
		into(mine, subdomainsApi.hygiene(projectId, scanId), (d) => (hygiene = d));

	let posture = $state<DomainPostureSummary | null>(null);
	const loadPosture = (mine: number) =>
		into(mine, domainPostureApi.scan(projectId, scanId), (d) => (posture = d));

	let hosting = $state<HostingComposition | null>(null);
	const loadHosting = (mine: number) =>
		into(mine, subdomainsApi.hosting(projectId, scanId), (d) => (hosting = d));

	const loadEstate = (mine: number) =>
		into(mine, targetsApi.getEstate(scan.target_id, projectId, scanId), (e) => (estate = e));

	let lookalikes = $state<LookalikeSummary | null>(null);
	const loadLookalikes = (mine: number) =>
		isDomain
			? into(mine, lookalikesApi.scan(projectId, scanId), (l) => (lookalikes = l))
			: Promise.resolve();

	async function reload() {
		if (!scanId || !projectId) return;
		const mine = ++generation;
		const waves = [
			[loadInsights, loadVulns, loadStructure],
			[loadExposure, loadOrigins, loadHosting, loadHygiene],
			[loadPosture, loadEstate, loadLookalikes]
		];
		for (const wave of waves) {
			if (mine !== generation) return;
			await Promise.allSettled(wave.map((load) => load(mine)));
		}
	}

	$effect(() => {
		void signature;
		if (!seen) return;
		untrack(() => void reload());
	});

	const liveRefresh = new LiveRefresh(() => void reload(), LIVE_OVERVIEW_MS);
	$effect(() => {
		liveRefresh.notify(revision, seen);
	});
	onDestroy(() => liveRefresh.stop());

	$effect(() => {
		if (!engineCatalogStore.hasFetched) untrack(() => engineCatalogStore.fetch());
	});

	const stat = (key: string) => insights?.surface.find((s) => s.key === key)?.value ?? null;
	let stats = $derived({
		assets: stat('subdomains'),
		resolved: stat('resolved'),
		live: stat('live'),
		web: stat('web'),
		ips: stat('ips'),
		ports: stat('ports'),
		networks: stat('asns')
	});
	let insightsFailed = $derived(errored && !insights);
	let empty = $derived(scanFoundNothing(scan));
	let emptyReason = $derived.by(() => {
		switch (scan.status) {
			case 'failed':
				return 'The scan failed.';
			case 'paused':
				return 'The scan is paused.';
			case 'cancelled':
				return 'The scan was cancelled.';
			default:
				return undefined;
		}
	});
</script>

<div class="flex flex-col gap-5">
	<HeroPanel
		{scan}
		{previous}
		{history}
		{historyLoaded}
		{stats}
		vulnTotal={vulns?.total ?? null}
		endpointTotal={structure?.endpoints ?? null}
		{run}
		{catalog}
		{activities}
		{previousDuration}
		{now}
		{scanId}
		{projectId}
		geography={insights?.geography ?? []}
		geoTotal={insights?.geo_total ?? 0}
		geoReady={!loading || insightsFailed}
		{onTab}
	/>

	{#if empty}
		{#if !live}
			<EmptyState compact icon={SearchX} title="No {nounPlural} found" description={emptyReason}>
				<Button variant="outline" size="sm" onclick={onRescan}>Rescan</Button>
			</EmptyState>
		{/if}
	{:else}
		{#if estate && estate.counts.untracked > 0}
			<EstateTray
				count={estate.counts.untracked}
				subject={scan.execution_config.target_value}
				domains={estate.domains}
				providers={estate.providers}
				neighbours={estate.neighbours}
			/>
		{/if}

		{#if lookalikes && lookalikes.registered > 0}
			<LookalikeTray
				summary={lookalikes}
				{projectId}
				onChanged={() => loadLookalikes(generation)}
			/>
		{/if}

		<AttentionPanel
			attention={insights?.attention ?? []}
			clusters={insights?.clusters ?? []}
			{origins}
			loading={loading && !insights}
			errored={insightsFailed}
			{onFilter}
			{onTab}
		/>

		{#if insightsFailed}
			<EmptyState compact icon={TriangleAlert} title="Scan insights not loaded">
				<Button variant="outline" size="sm" onclick={() => loadInsights(generation)}>Retry</Button>
			</EmptyState>
		{:else}
			<VulnerabilityPanel {vulns} {onTab} />
			<HostingPanel {hosting} onPick={(q) => onTab(WEB.tab, q)} />
			<PosturePanel {insights} {loading} {isDomain} {nounPlural} {onFilter} />
			<HygienePanel summary={hygiene} loading={loading && !hygiene} {onFilter} />
			<DomainPosturePanel summary={posture} loading={loading && !posture} {onFilter} />
			<ExposurePanel {exposure} {loading} {onTab} />
			<StructurePanel {structure} {loading} {onTab} />
			<CompositionPanel {insights} {loading} {scanId} {projectId} {onFilter} />
		{/if}
	{/if}
</div>
