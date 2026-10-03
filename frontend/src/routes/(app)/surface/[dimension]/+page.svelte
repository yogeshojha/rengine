<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { afterNavigate, goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
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
	import SecretsTable from '$lib/components/scans/results/secrets-table.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import {
		FINDINGS_TABS,
		SURFACE_ORDER,
		SurfaceDimension,
		type FindingsTab,
		type ResultTab
	} from '$lib/config/surface';
	import { ROUTES, routeLabels } from '$lib/config/routes';

	let spec = $derived(SURFACE_ORDER.find((s) => s.tab === page.params.dimension) ?? null);
	const FINDINGS_KEYS = new Set<string>(FINDINGS_TABS.map((t) => t.key));
	let findingsTab = $derived(
		spec && FINDINGS_KEYS.has(spec.key) ? (spec.key as FindingsTab) : null
	);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let coverage = $derived(spec ? surfaceStore.coverage(spec.key) : null);

	let visit = $state(0);
	afterNavigate(({ type, from, to }) => {
		if (type !== 'link' && type !== 'goto') return;
		if (from?.url.pathname === to?.url.pathname) visit += 1;
	});

	let launchIds = $state<string[]>([]);
	let launchOpen = $state(false);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void surfaceStore.load(id));
	});

	function openTab(tab: ResultTab, filter?: string) {
		const target = SURFACE_ORDER.find((s) => s.tab === tab);
		if (!target) return;
		void goto(ROUTES.surface(tab, filter ? { [target.queryParam]: filter } : undefined));
	}

	function afterLaunch() {
		launchOpen = false;
		if (projectId) void surfaceStore.load(projectId, true);
	}
</script>

<svelte:head><title>{pageTitle(spec?.label ?? routeLabels.surface)}</title></svelte:head>

{#if !spec}
	<EmptyState title="Unknown dimension">
		<Button variant="outline" size="sm" href={ROUTES.surface('web-assets')}>Web assets</Button>
	</EmptyState>
{:else}
	<div class="flex flex-col gap-6">
		{#if findingsTab}
			<FindingsTabs value={findingsTab} />
		{:else}
			<h1 class="text-2xl font-semibold tracking-tight">{spec.label}</h1>
		{/if}

		<div class="overflow-hidden rounded-xl border bg-card">
			<ScopeStrip
				{coverage}
				error={surfaceStore.error}
				onRetry={() => {
					if (projectId) void surfaceStore.load(projectId, true);
				}}
				onScanUncovered={(ids) => {
					launchIds = ids;
					launchOpen = true;
				}}
			/>
		</div>

		<div>
			{#key `${projectId}:${spec.key}:${visit}`}
				{#if spec.key === SurfaceDimension.WEB_ASSETS}
					<WebAssetsTable scanId="" projectWide {projectId} onTab={openTab} />
				{:else if spec.key === SurfaceDimension.ENDPOINTS}
					<EndpointsTable scanId="" projectWide {projectId} onTab={openTab} />
				{:else if spec.key === SurfaceDimension.SERVICES}
					<ServicesTable scanId="" projectWide {projectId} onTab={openTab} />
				{:else if spec.key === SurfaceDimension.IPS}
					<IpsTable scanId="" projectWide {projectId} onTab={openTab} />
				{:else if spec.key === SurfaceDimension.VULNERABILITIES}
					<VulnerabilitiesTable scanId="" projectWide onTab={openTab} />
				{:else if spec.key === SurfaceDimension.SECRETS}
					<SecretsTable scanId="" projectWide {projectId} />
				{:else}
					<SoftwareTable scanId="" projectWide {projectId} />
				{/if}
			{/key}
		</div>
	</div>

	<LaunchDialog bind:open={launchOpen} targetIds={launchIds} onClose={afterLaunch} />
{/if}
