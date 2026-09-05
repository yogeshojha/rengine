<script lang="ts">
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
	import FileSearch from '@lucide/svelte/icons/file-search';
	import History from '@lucide/svelte/icons/history';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	import { targetsApi } from '$lib/api/targets';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { activityScope } from '$lib/stores/activity-scope.svelte';
	import { TargetType } from '$lib/types/target';
	import type { Target } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import type { TargetSummaryRead } from '$lib/types/target-summary';
	import type { ScanRead } from '$lib/types/scan';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Kbd } from '$lib/components/ui/kbd';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScanActivityChart from '$lib/components/scans/scan-activity-chart.svelte';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import TargetHeader from '$lib/components/targets/target-detail/target-header.svelte';
	import TargetHeaderSkeleton from '$lib/components/targets/target-detail/target-header-skeleton.svelte';
	import EnrichmentWidget from '$lib/components/targets/target-detail/enrichment/enrichment-widget.svelte';
	import WhoisSection from '$lib/components/targets/target-detail/enrichment/whois-section.svelte';
	import DnsSection from '$lib/components/targets/target-detail/enrichment/dns-section.svelte';
	import BgpSection from '$lib/components/targets/target-detail/enrichment/bgp-section.svelte';
	import SurfacePanel from '$lib/components/targets/target-detail/summary/surface-panel.svelte';
	import RiskPanel from '$lib/components/targets/target-detail/summary/risk-panel.svelte';
	import TargetVitals from '$lib/components/targets/target-detail/summary/target-vitals.svelte';
	import SecurityPosture from '$lib/components/targets/target-detail/summary/security-posture.svelte';
	import TargetInfra from '$lib/components/targets/target-detail/summary/target-infra.svelte';
	import TargetMeta from '$lib/components/targets/target-detail/summary/target-meta.svelte';
	import TargetWebAssets from '$lib/components/targets/target-detail/target-web-assets.svelte';
	import { buildTargetSummary } from '$lib/components/targets/target-detail/summary/derive';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { downloadBlob } from '$lib/utilities/download';
	import type { IconComponent } from '$lib/config/icons';

	const TABS = ['summary', 'web-assets', 'intelligence', 'scans'] as const;
	type TabKey = (typeof TABS)[number];
	const TAB_DEFS: { key: TabKey; label: string; icon: IconComponent }[] = [
		{ key: 'summary', label: 'Summary', icon: LayoutDashboard },
		{
			key: 'web-assets',
			label: SURFACE[SurfaceDimension.WEB_ASSETS].label,
			icon: SURFACE[SurfaceDimension.WEB_ASSETS].icon
		},
		{ key: 'intelligence', label: 'Intelligence', icon: FileSearch },
		{ key: 'scans', label: 'Scans', icon: History }
	];
	const ENRICHMENT_POLL_MS = 2500;
	const MAX_ENRICHMENT_POLLS = 30;

	const targetId = $derived(page.params.id ?? '');

	let target = $state<Target | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let showLaunchModal = $state(false);

	let detail = $state<TargetDetailRead | null>(null);
	let detailLoading = $state(true);
	let detailError = $state<string | null>(null);
	let summary = $state<TargetSummaryRead | null>(null);
	let summaryLoading = $state(true);
	let refreshingDns = $state(false);
	let refreshingWhois = $state(false);
	let refreshingBgp = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let tabsHeight = $state(0);

	let showDns = $derived(
		target?.target_type === TargetType.DOMAIN || target?.target_type === TargetType.URL
	);
	let showBgp = $derived(
		target?.target_type === TargetType.IP ||
			target?.target_type === TargetType.IP_RANGE ||
			target?.target_type === TargetType.ASN
	);

	let whoisStatus = $derived(detail?.whois_status ?? target?.whois_status ?? TaskStatus.PENDING);
	let dnsStatus = $derived(detail?.dns_status ?? target?.dns_status ?? TaskStatus.PENDING);
	let bgpStatus = $derived(detail?.bgp_status ?? target?.bgp_status ?? TaskStatus.PENDING);

	const initialTab = page.url.searchParams.get('tab');
	let activeTab = $state<TabKey>(
		TABS.includes(initialTab as TabKey) ? (initialTab as TabKey) : 'summary'
	);

	let hasInfra = $derived(target ? buildTargetSummary(target, detail).infra.length > 0 : false);
	let riskCovered = $derived(!!summary?.risk.scan_id);
	let tabCounts = $derived<Partial<Record<TabKey, number>>>(
		summary ? { 'web-assets': summary.inventory_total, scans: summary.scans_total } : {}
	);

	function setTab(value: string) {
		if (!value) return;
		activeTab = value as TabKey;
		if (!browser) return;
		const params = new SvelteURLSearchParams(untrack(() => page.url.searchParams));
		if (value === 'summary') params.delete('tab');
		else params.set('tab', value);
		const query = params.toString();
		try {
			replaceState(query ? `?${query}` : location.pathname, {});
		} catch {
			// history is unavailable during hydration
		}
	}

	async function fetchTarget() {
		isLoading = true;
		error = null;
		try {
			target = await targetsApi.get(targetId);
			breadcrumbStore.set(targetId, target.target_value);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load target';
		} finally {
			isLoading = false;
		}
	}

	async function fetchDetail(silent = false) {
		if (!silent) detailLoading = true;
		try {
			detail = await targetsApi.getDetail(targetId);
			detailError = null;
		} catch (e) {
			detailError = e instanceof Error ? e.message : 'Failed to load enrichment details';
		} finally {
			if (!silent) detailLoading = false;
		}
	}

	async function fetchSummary(silent = false) {
		const project = projectsStore.activeProject;
		if (!project) return;
		if (!silent) summaryLoading = true;
		try {
			summary = await targetsApi.getSummary(targetId, project.id);
		} catch {
			summary = null;
		} finally {
			if (!silent) summaryLoading = false;
		}
	}

	function hasPendingEnrichment(): boolean {
		const inFlight = (s: TaskStatus) => s === TaskStatus.PENDING || s === TaskStatus.QUERYING;
		if (inFlight(whoisStatus)) return true;
		if (showDns && inFlight(dnsStatus)) return true;
		if (showBgp && inFlight(bgpStatus)) return true;
		return false;
	}

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	}

	function startPolling() {
		stopPolling();
		let attempts = 0;
		pollTimer = setInterval(async () => {
			attempts += 1;
			await fetchDetail(true);
			if (!hasPendingEnrichment() || attempts >= MAX_ENRICHMENT_POLLS) stopPolling();
		}, ENRICHMENT_POLL_MS);
	}

	$effect(() => {
		if (targetId) {
			fetchTarget();
			fetchDetail();
		}
		activityScope.targetId = targetId;
		return () => activityScope.clear();
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = targetId;
		if (project && id) untrack(() => fetchSummary());
	});

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => fetchSummary(true));
	});

	onDestroy(() => {
		stopPolling();
		if (targetId) breadcrumbStore.remove(targetId);
	});

	function handleScan() {
		if (!target) return;
		showLaunchModal = true;
	}

	async function handleRefreshEnrichment() {
		if (!target) return;
		toast.info('Enrichment refresh started');
		const requests: Promise<unknown>[] = [targetsApi.refreshWhois(target.id)];
		if (showDns) requests.push(targetsApi.refreshDns(target.id));
		if (showBgp) requests.push(targetsApi.refreshBgp(target.id));
		const results = await Promise.allSettled(requests);
		const failed = results.filter((r) => r.status === 'rejected').length;
		if (failed > 0) {
			toast.error(
				failed === results.length
					? 'Enrichment refresh failed'
					: `${failed} of ${results.length} lookups failed to start`
			);
		}
		startPolling();
	}

	async function refreshOne(
		kind: 'DNS' | 'WHOIS' | 'BGP',
		call: (id: string) => Promise<unknown>,
		set: (value: boolean) => void
	) {
		if (!target) return;
		set(true);
		try {
			await call(target.id);
			toast.success(`${kind} refresh started`);
			startPolling();
		} catch {
			toast.error(`${kind} refresh failed`);
		} finally {
			set(false);
		}
	}

	const fileName = (ext: string) =>
		`${(target?.target_value ?? 'target').replace(/[^a-z0-9.-]+/gi, '_')}.${ext}`;

	function handleExportJson() {
		if (!target) return;
		downloadBlob(
			fileName('json'),
			JSON.stringify({ target, detail, summary }, null, 2),
			'application/json'
		);
		toast.success('Exported target as JSON');
	}

	function handleExportCsv() {
		if (!target) return;
		const rows: [string, string][] = [
			['target_value', target.target_value],
			['target_type', target.target_type],
			['display_name', target.display_name ?? ''],
			['whois_status', target.whois_status],
			['dns_status', target.dns_status],
			['bgp_status', target.bgp_status],
			['organizations', target.organizations.map((o) => o.name).join('; ')],
			['tags', target.tags.map((t) => t.name).join('; ')],
			['scans', String(summary?.scans_total ?? 0)],
			...(summary?.surface ?? []).map(
				(m) =>
					[m.label.toLowerCase().replace(/\s+/g, '_'), String(m.value ?? '')] as [string, string]
			),
			['created_at', target.created_at],
			['updated_at', target.updated_at]
		];
		const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
		const csv = ['field,value', ...rows.map(([k, v]) => `${esc(k)},${esc(v)}`)].join('\n');
		downloadBlob(fileName('csv'), csv, 'text/csv');
		toast.success('Exported target as CSV');
	}

	async function confirmDelete() {
		if (!target) return;
		isDeleting = true;
		try {
			await targetsApi.delete(target.id);
			toast.success(`Target ${target.target_value} deleted`);
			showDeleteDialog = false;
			goto(ROUTES.targets);
		} catch {
			toast.error('Failed to delete target');
		} finally {
			isDeleting = false;
		}
	}

	function rescan(_scan: ScanRead) {
		handleScan();
	}
</script>

{#snippet enrichmentError()}
	{#if detailError && !detailLoading}
		<div
			class="flex items-center justify-between gap-3 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3"
		>
			<div class="flex items-center gap-2">
				<span class="flex h-5 shrink-0 items-center">
					<TriangleAlert class="size-4 text-destructive" />
				</span>
				<p class="text-sm text-destructive">
					Enrichment details could not be loaded. {detailError}
				</p>
			</div>
			<Button variant="outline" size="sm" class="gap-2" onclick={() => fetchDetail()}>
				<RefreshCw class="size-3.5" /> Retry
			</Button>
		</div>
	{/if}
{/snippet}

{#if isLoading}
	<TargetHeaderSkeleton />
{:else if error}
	<Empty.Root class="min-h-[50vh] border-none">
		<Empty.Header>
			<Empty.Media
				variant="icon"
				class="size-16 rounded-full bg-destructive/10 text-destructive [&_svg:not([class*='size-'])]:size-8"
			>
				<TriangleAlert />
			</Empty.Media>
			<Empty.Title>Target not found</Empty.Title>
			<Empty.Description class="max-w-md">{error}</Empty.Description>
		</Empty.Header>
		<Empty.Content>
			<Button variant="outline" class="gap-2" onclick={() => goto(ROUTES.targets)}>
				<ChevronLeft class="size-4" />
				Back to targets
			</Button>
		</Empty.Content>
	</Empty.Root>
{:else if target}
	<div class="flex flex-col gap-5">
		<TargetHeader
			{target}
			onScan={handleScan}
			onRefreshEnrichment={handleRefreshEnrichment}
			onExportJson={handleExportJson}
			onExportCsv={handleExportCsv}
			onDelete={() => (showDeleteDialog = true)}
		/>

		<Tabs.Root value={activeTab} onValueChange={setTab} style="--target-tabs-h: {tabsHeight}px">
			<div
				bind:clientHeight={tabsHeight}
				class="sticky top-0 z-30 -mx-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:-mx-6 md:px-6"
			>
				<Tabs.List class="h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
					{#each TAB_DEFS as t, i (t.key)}
						{@const n = tabCounts[t.key]}
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Tabs.Trigger
										{...props}
										value={t.key}
										class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
									>
										<t.icon class="size-3.5" />
										{t.label}
										{#if n != null}
											<span
												class="text-xs tabular-nums {n === 0
													? 'text-muted-foreground/50'
													: 'text-muted-foreground'}"
											>
												{n.toLocaleString()}
											</span>
										{/if}
									</Tabs.Trigger>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content side="bottom" class="flex items-center gap-1.5">
								{t.label}
								<Kbd>{i + 1}</Kbd>
							</Tooltip.Content>
						</Tooltip.Root>
					{/each}
				</Tabs.List>
			</div>

			<Tabs.Content value="summary" class="mt-5 flex flex-col gap-4">
				{@render enrichmentError()}
				<SurfacePanel
					{summary}
					loading={summaryLoading}
					onScan={handleScan}
					onTab={(tab) => setTab(tab)}
				/>
				{#if riskCovered && summary}
					<RiskPanel risk={summary.risk} />
				{/if}
				<TargetVitals {target} {detail} loading={detailLoading} />
				<div class="grid grid-cols-1 items-start gap-4 {hasInfra ? 'lg:grid-cols-2' : ''}">
					<SecurityPosture {target} {detail} loading={detailLoading} />
					{#if hasInfra}
						<TargetInfra {target} {detail} />
					{/if}
				</div>
			</Tabs.Content>

			<Tabs.Content value="web-assets" class="mt-5">
				<TargetWebAssets targetId={target.id} onScan={handleScan} />
			</Tabs.Content>

			<Tabs.Content value="intelligence" class="mt-5 flex flex-col gap-4">
				{@render enrichmentError()}
				<div class="grid grid-cols-1 items-start gap-4 {showDns ? 'lg:grid-cols-2' : ''}">
					{#if showDns}
						<EnrichmentWidget
							title="DNS"
							status={dnsStatus}
							error={detail?.dns_error}
							queriedAt={detail?.dns?.queried_at}
							onRefresh={() => refreshOne('DNS', targetsApi.refreshDns, (v) => (refreshingDns = v))}
							isRefreshing={refreshingDns}
							loading={detailLoading}
						>
							{#if detail?.dns}
								<DnsSection lookup={detail.dns} />
							{/if}
						</EnrichmentWidget>
					{/if}
					<EnrichmentWidget
						title="WHOIS"
						status={whoisStatus}
						error={detail?.whois_error}
						queriedAt={detail?.whois?.queried_at}
						onRefresh={() =>
							refreshOne('WHOIS', targetsApi.refreshWhois, (v) => (refreshingWhois = v))}
						isRefreshing={refreshingWhois}
						loading={detailLoading}
					>
						{#if detail?.whois}
							<WhoisSection record={detail.whois} targetType={target.target_type} />
						{/if}
					</EnrichmentWidget>
				</div>
				{#if showBgp}
					<EnrichmentWidget
						title="BGP"
						status={bgpStatus}
						onRefresh={() => refreshOne('BGP', targetsApi.refreshBgp, (v) => (refreshingBgp = v))}
						isRefreshing={refreshingBgp}
						loading={detailLoading}
					>
						{#if detail?.bgp}
							<BgpSection bgp={detail.bgp} />
						{/if}
					</EnrichmentWidget>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="scans" class="mt-5 flex flex-col gap-4">
				<ScanActivityChart stats={scansStore.stats} />
				<ScanHistoryTable targetId={target.id} onLaunch={handleScan} onRescan={rescan} />
			</Tabs.Content>
		</Tabs.Root>

		<TargetMeta {target} />
	</div>

	<LaunchDialog
		bind:open={showLaunchModal}
		targetId={target.id}
		onClose={() => {
			showLaunchModal = false;
			fetchSummary(true);
			scansStore.refresh();
		}}
	/>

	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete this target?"
		description="This also deletes every scan and finding for {target.target_value}."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={confirmDelete}
	/>
{/if}
