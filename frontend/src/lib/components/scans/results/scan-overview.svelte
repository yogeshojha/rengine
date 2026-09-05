<script lang="ts">
	import { untrack } from 'svelte';
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
	import { subdomainsApi } from '$lib/api/subdomains';
	import { endpointsApi, servicesApi } from '$lib/api/scan-results';
	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import { targetAssetNoun, TargetType } from '$lib/types/target';
	import type { RelatedDomains } from '$lib/types/asset-query';
	import { scanFoundNothing } from '$lib/types/scan';
	import type { ScanActivityRead, ScanCommandRead, ScanRead } from '$lib/types/scan';
	import type { SubdomainInsights } from '$lib/utilities/scan-insights';
	import type { ScanExposure } from '$lib/utilities/services';
	import type { ScanStructure } from '$lib/utilities/endpoints';
	import type { ScanVulnerabilities } from '$lib/utilities/vulns';
	import type { OriginExposure } from '$lib/utilities/origins';

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
		onFilter: (search: string) => void;
		onTab: (tab: string, filter?: string) => void;
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
		onFilter,
		onTab,
		onRescan
	}: Props = $props();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let insights = $state<SubdomainInsights | null>(null);
	let relatedDomains = $state<RelatedDomains | null>(null);
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
	let revision = $derived(
		[
			scan.status,
			scan.subdomains_found,
			scan.ips_found,
			scan.http_assets_found,
			scan.open_ports_found
		].join(':')
	);

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
		if (!scanId) return;
		vulnerabilitiesApi
			.overview(scanId)
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

	function loadRelated() {
		if (!scanId || !projectId) return;
		subdomainsApi
			.relatedDomains(projectId, scanId)
			.then((d) => (relatedDomains = d))
			.catch(() => (relatedDomains = null));
	}

	$effect(() => {
		void revision;
		void scanId;
		void projectId;
		if (!seen) return;
		untrack(() => {
			loadInsights();
			loadRelated();
			loadExposure();
			loadStructure();
			loadVulns();
			loadOrigins();
		});
	});

	$effect(() => {
		if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
	});

	const stat = (key: string) => insights?.surface.find((s) => s.key === key)?.value ?? null;
	let stats = $derived({
		resolved: stat('resolved'),
		live: stat('live'),
		web: stat('web'),
		networks: stat('asns')
	});
	let insightsFailed = $derived(errored && !insights);
	let empty = $derived(scanFoundNothing(scan));
	let emptyReason = $derived.by(() => {
		switch (scan.status) {
			case 'failed':
				return `The scan failed before it found anything for ${scan.execution_config.target_value}.`;
			case 'cancelled':
				return `The scan was stopped before it found anything for ${scan.execution_config.target_value}.`;
			default:
				return `This scan found no ${nounPlural} for ${scan.execution_config.target_value}.`;
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
		<AttentionPanel
			attention={insights?.attention ?? []}
			clusters={insights?.clusters ?? []}
			related={relatedDomains?.domains ?? []}
			{origins}
			loading={loading && !insights}
			errored={insightsFailed}
			{onFilter}
			{onTab}
		/>

		{#if insightsFailed}
			<EmptyState compact icon={TriangleAlert} title="Scan insights could not be loaded">
				<Button variant="outline" size="sm" onclick={loadInsights}>Retry</Button>
			</EmptyState>
		{:else}
			<VulnerabilityPanel {vulns} {onTab} />
			<PosturePanel {insights} {loading} {isDomain} {nounPlural} {onFilter} />
			<ExposurePanel {exposure} {loading} {onTab} />
			<StructurePanel {structure} {loading} {onTab} />
			<CompositionPanel {insights} {loading} {scan} {scanId} {projectId} {onFilter} {onTab} />
		{/if}
	{/if}
</div>
