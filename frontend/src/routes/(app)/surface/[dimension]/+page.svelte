<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScopeStrip from '$lib/components/surface/scope-strip.svelte';
	import FindingsTabs from '$lib/components/surface/findings-tabs.svelte';
	import WebAssetsTable from '$lib/components/scans/results/web-assets-table.svelte';
	import EndpointsTable from '$lib/components/scans/results/endpoints-table.svelte';
	import ServicesTable from '$lib/components/scans/results/services-table.svelte';
	import IpsTable from '$lib/components/scans/results/ips-table.svelte';
	import VulnerabilitiesTable from '$lib/components/scans/results/vulnerabilities-table.svelte';
	import SoftwareTable from '$lib/components/scans/results/software-table.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import {
		FINDINGS_TABS,
		SURFACE_ORDER,
		SurfaceDimension,
		type FindingsTab
	} from '$lib/config/surface';
	import { ROUTES } from '$lib/config/routes';

	let spec = $derived(SURFACE_ORDER.find((s) => s.tab === page.params.dimension) ?? null);
	const FINDINGS_KEYS = new Set<string>(FINDINGS_TABS.map((t) => t.key));
	let findingsTab = $derived(
		spec && FINDINGS_KEYS.has(spec.key) ? (spec.key as FindingsTab) : null
	);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let coverage = $derived(spec ? surfaceStore.coverage(spec.key) : null);

	let launchIds = $state<string[]>([]);
	let launchOpen = $state(false);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void surfaceStore.load(id));
	});

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
		{#if findingsTab}
			<FindingsTabs value={findingsTab} />
		{:else}
			<h1 class="text-2xl font-semibold tracking-tight">{spec.label}</h1>
		{/if}

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
				<WebAssetsTable scanId="" projectWide {projectId} />
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
