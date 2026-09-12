<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScopeStrip from '$lib/components/surface/scope-strip.svelte';
	import WebAssetsTable from '$lib/components/scans/results/web-assets-table.svelte';
	import HygienePanel from '$lib/components/scans/results/overview/hygiene-panel.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import {
		emptyQuery,
		type HygieneSummary,
		type WebAssetQuery
	} from '$lib/utilities/scan-insights';
	import EndpointsTable from '$lib/components/scans/results/endpoints-table.svelte';
	import ServicesTable from '$lib/components/scans/results/services-table.svelte';
	import IpsTable from '$lib/components/scans/results/ips-table.svelte';
	import VulnerabilitiesTable from '$lib/components/scans/results/vulnerabilities-table.svelte';
	import SoftwareTable from '$lib/components/scans/results/software-table.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import { SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
	import { ROUTES } from '$lib/config/routes';

	let spec = $derived(SURFACE_ORDER.find((s) => s.tab === page.params.dimension) ?? null);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let coverage = $derived(spec ? surfaceStore.coverage(spec.key) : null);

	let launchIds = $state<string[]>([]);
	let launchOpen = $state(false);
	let webQuery = $state<WebAssetQuery>(emptyQuery());
	let hygiene = $state<HygieneSummary | null>(null);
	let hygieneLoading = $state(false);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void surfaceStore.load(id));
	});

	$effect(() => {
		const id = projectId;
		if (!id || spec?.key !== SurfaceDimension.WEB_ASSETS) return;
		untrack(() => loadHygiene(id));
	});

	function loadHygiene(id: string) {
		hygieneLoading = true;
		subdomainsApi
			.hygiene(id, '')
			.then((d) => (hygiene = d))
			.catch(() => (hygiene = null))
			.finally(() => (hygieneLoading = false));
	}

	function afterLaunch() {
		launchOpen = false;
		if (projectId) void surfaceStore.load(projectId, true);
	}
</script>

{#if !spec}
	<EmptyState title="Unknown dimension">
		<a href={ROUTES.surface('web-assets')} class="text-sm underline">Web assets</a>
	</EmptyState>
{:else}
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight">{spec.label}</h1>
				<p class="mt-1 text-sm text-muted-foreground">
					Every {spec.noun} in this project from the latest scan of each target
				</p>
			</div>
		</div>

		<div class="overflow-hidden rounded-xl border bg-card">
			<ScopeStrip
				{coverage}
				onScanUncovered={(ids) => {
					launchIds = ids;
					launchOpen = true;
				}}
			/>
		</div>

		{#key `${projectId}:${spec.key}`}
			{#if spec.key === SurfaceDimension.WEB_ASSETS}
				<HygienePanel
					summary={hygiene}
					loading={hygieneLoading}
					onFilter={(search) => (webQuery = { ...emptyQuery(), search })}
				/>
				<WebAssetsTable scanId="" projectWide {projectId} bind:query={webQuery} />
			{:else if spec.key === SurfaceDimension.ENDPOINTS}
				<EndpointsTable scanId="" projectWide {projectId} />
			{:else if spec.key === SurfaceDimension.SERVICES}
				<ServicesTable scanId="" projectWide {projectId} />
			{:else if spec.key === SurfaceDimension.IPS}
				<IpsTable scanId="" projectWide {projectId} />
			{:else if spec.key === SurfaceDimension.VULNERABILITIES}
				<VulnerabilitiesTable scanId="" projectWide />
			{:else}
				<SoftwareTable scanId="" projectWide {projectId} />
			{/if}
		{/key}
	</div>

	<LaunchDialog bind:open={launchOpen} targetIds={launchIds} onClose={afterLaunch} />
{/if}
