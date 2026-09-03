<script lang="ts">
	import { untrack } from 'svelte';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import EmptyState from '$lib/components/empty-state.svelte';
	import HeroPanel from './overview/hero-panel.svelte';
	import AttentionPanel from './overview/attention-panel.svelte';
	import PosturePanel from './overview/posture-panel.svelte';
	import CompositionPanel from './overview/composition-panel.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import { targetAssetNoun, TargetType } from '$lib/types/target';
	import type { RelatedDomains } from '$lib/types/asset-query';
	import type { ScanActivityRead, ScanCommandRead, ScanRead } from '$lib/types/scan';
	import type { SubdomainInsights } from '$lib/utilities/scan-insights';

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

	const ASSESSING_STAGE = 'http_probe';

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let insights = $state<SubdomainInsights | null>(null);
	let relatedDomains = $state<RelatedDomains | null>(null);
	let loading = $state(true);
	let errored = $state(false);

	let live = $derived(isLiveStatus(scan.status));
	let run = $derived(live ? liveScans.runFor(scan.id) : undefined);
	let catalog = $derived(engineCatalogStore.stages);
	let type = $derived(scan.execution_config.target_type);
	let nounPlural = $derived(targetAssetNoun(type));
	let isDomain = $derived(type === TargetType.DOMAIN);
	let assessed = $derived(
		activities.some((a) => a.name === ASSESSING_STAGE && a.status === 'success')
	);
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

	<AttentionPanel
		{scan}
		attention={insights?.attention ?? []}
		clusters={insights?.clusters ?? []}
		related={relatedDomains?.domains ?? []}
		{assessed}
		{live}
		loading={loading && !insights}
		errored={insightsFailed}
		{onFilter}
		{onRescan}
		onRetry={loadInsights}
	/>

	{#if insightsFailed}
		<EmptyState compact icon={TriangleAlert} title="Scan insights could not be loaded">
			<Button variant="outline" size="sm" onclick={loadInsights}>Retry</Button>
		</EmptyState>
	{:else}
		<PosturePanel {insights} {loading} {isDomain} {nounPlural} {onFilter} />
		<CompositionPanel {insights} {loading} {scan} {scanId} {projectId} {onFilter} {onTab} />
	{/if}
</div>
