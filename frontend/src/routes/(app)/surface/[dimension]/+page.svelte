<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { afterNavigate, goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import Radar from '@lucide/svelte/icons/radar';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
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
	import type { TableColumn } from '$lib/components/scans/results/table/columns';

	let spec = $derived(SURFACE_ORDER.find((s) => s.tab === page.params.dimension) ?? null);
	const FINDINGS_KEYS = new Set<string>(FINDINGS_TABS.map((t) => t.key));
	let findingsTab = $derived(
		spec && FINDINGS_KEYS.has(spec.key) ? (spec.key as FindingsTab) : null
	);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let coverage = $derived(spec ? surfaceStore.coverage(spec.key) : null);
	// nothing scanned yet: one empty state instead of a toolbar of zeroes
	let unscanned = $derived(coverage !== null && coverage.targets_covered === 0);
	let things = $derived(
		spec?.key === SurfaceDimension.IPS ? 'IP addresses' : (spec?.nounPlural ?? '')
	);

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

	const LOADING_LEAD: TableColumn[] = [
		{ key: 'name', label: '', width: 'min-w-0 flex-1', grow: true }
	];
	const LOADING_COLUMNS: TableColumn[] = [
		{ key: 'a', label: '', width: 'w-32' },
		{ key: 'b', label: '', width: 'w-24' },
		{ key: 'c', label: '', width: 'w-28' }
	];

	function retry() {
		visit += 1;
		if (projectId) void surfaceStore.load(projectId, true);
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
			<PageHeader title={spec.label} />
		{/if}

		{#if !coverage && surfaceStore.error}
			<EmptyState
				icon={TriangleAlert}
				title="{spec.label} not loaded"
				description={surfaceStore.error}
			>
				<Button variant="outline" size="sm" onclick={retry}>Retry</Button>
			</EmptyState>
		{:else if !coverage}
			<div class="flex flex-col gap-6" aria-busy="true">
				<div class="rounded-xl border bg-card px-4 py-2">
					<Skeleton class="h-4 w-56 max-w-full" />
				</div>
				<div class="overflow-hidden rounded-xl border bg-card">
					<div class="flex min-h-14 items-center gap-3 border-b bg-muted/30 px-4 py-2">
						<Skeleton class="size-8 shrink-0 rounded-lg" />
						<Skeleton class="h-4 w-full max-w-80" />
					</div>
					<TableSkeleton lead={LOADING_LEAD} columns={LOADING_COLUMNS} selectable />
				</div>
			</div>
		{:else if unscanned}
			<EmptyState
				icon={spec.icon}
				title="No {things} yet"
				description="{things.charAt(0).toUpperCase()}{things.slice(1)} appear after a scan."
			>
				<Button
					size="sm"
					onclick={() => {
						launchIds = coverage?.uncovered.map((t) => t.target_id) ?? [];
						launchOpen = true;
					}}
				>
					<Radar class="size-3.5" />
					Start scan
				</Button>
			</EmptyState>
		{:else}
			<div class="overflow-hidden rounded-xl border bg-card">
				<ScopeStrip
					{coverage}
					error={surfaceStore.error}
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
		{/if}
	</div>

	<LaunchDialog bind:open={launchOpen} targetIds={launchIds} onClose={afterLaunch} />
{/if}
