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
	import type { ScanActivityRead, ScanCommandRead, ScanRead } from '$lib/types/scan';
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
		commands: ScanCommandRead[];
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
		commands,
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
	let nounPlural = $derived(targetAssetNoun(type));
	let isDomain = $derived(type === TargetType.DOMAIN);
	let signature = $derived([scanId, projectId, scan.status].join(':'));

	function loadInsights() {
		if (!scanId || !projectId) return;
		if (!insights) loading = true;
		errored = false;
		subdomainsApi
			.insights(projectId, scanId)
			.then((d) => {
				insights = d;
				errored = false;
			})
			.catch(() => {
				if (!insights) errored = true;
			})
			.finally(() => (loading = false));
	}

	function loadExposure() {
		if (!scanId || !projectId) return;
		servicesApi
			.exposure(projectId, scanId)
			.then((d) => (exposure = d))
			.catch(() => (exposure = null));
	}

	function loadStructure() {
		if (!scanId || !projectId) return;
		endpointsApi
			.structure(projectId, scanId)
			.then((d) => (structure = d))
			.catch(() => (structure = null));
	}

	function loadVulns() {
		if (!scanId || !projectId) return;
		vulnerabilitiesApi
			.overview(projectId, scanId)
			.then((d) => (vulns = d))
			.catch(() => (vulns = null));
	}

	function loadOrigins() {
		if (!scanId || !projectId) return;
		servicesApi
			.origins(projectId, scanId)
			.then((d) => (origins = d))
			.catch(() => (origins = null));
	}

	let hygiene = $state<HygieneSummary | null>(null);
	function loadHygiene() {
		if (!scanId || !projectId) return;
		subdomainsApi
			.hygiene(projectId, scanId)
			.then((d) => (hygiene = d))
			.catch(() => (hygiene = null));
	}

	let posture = $state<DomainPostureSummary | null>(null);
	function loadPosture() {
		if (!scanId || !projectId) return;
		domainPostureApi
			.scan(projectId, scanId)
			.then((d) => (posture = d))
			.catch(() => (posture = null));
	}

	let hosting = $state<HostingComposition | null>(null);
	function loadHosting() {
		if (!scanId || !projectId) return;
		subdomainsApi
			.hosting(projectId, scanId)
			.then((d) => (hosting = d))
			.catch(() => (hosting = null));
	}

	function loadEstate() {
		if (!scanId || !projectId) return;
		targetsApi
			.getEstate(scan.target_id, projectId, scanId)
			.then((e) => (estate = e))
			.catch(() => (estate = null));
	}

	function reload() {
		loadInsights();
		loadEstate();
		loadHosting();
		loadHygiene();
		loadPosture();
		loadExposure();
		loadStructure();
		loadVulns();
		loadOrigins();
	}

	$effect(() => {
		void signature;
		if (!seen) return;
		untrack(reload);
	});

	const liveRefresh = new LiveRefresh(reload, LIVE_OVERVIEW_MS);
	$effect(() => {
		liveRefresh.notify(revision, seen);
	});
	onDestroy(() => liveRefresh.stop());

	$effect(() => {
		if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
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
		{run}
		{catalog}
		{activities}
		{commands}
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
				<Button variant="outline" size="sm" onclick={onRescan}>Re-scan</Button>
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
				sheetDescription="{estate.domains.length} domains · {estate.providers
					.length} providers · {estate.considered_targets} targets considered"
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
				<Button variant="outline" size="sm" onclick={loadInsights}>Retry</Button>
			</EmptyState>
		{:else}
			<VulnerabilityPanel {vulns} {onTab} />
			<HostingPanel {hosting} onPick={(q) => onTab(WEB.tab, q)} />
			<PosturePanel {insights} {loading} {isDomain} {nounPlural} {onFilter} />
			<HygienePanel summary={hygiene} loading={loading && !hygiene} {onFilter} />
			<DomainPosturePanel summary={posture} loading={loading && !posture} {onFilter} />
			<ExposurePanel {exposure} {loading} {onTab} />
			<StructurePanel {structure} {loading} {onTab} />
			<CompositionPanel {insights} {loading} {scan} {scanId} {projectId} {onFilter} />
		{/if}
	{/if}
</div>
