<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Globe from '@lucide/svelte/icons/globe';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import Copy from '@lucide/svelte/icons/copy';
	import FileText from '@lucide/svelte/icons/file-text';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';

	import { scansApi } from '$lib/api/scans';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ScanEvent } from '$lib/types/sse';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Kbd } from '$lib/components/ui/kbd';
	import ScanStatusBadge from '@/components/scan-status-badge.svelte';
	import ConfirmDialog from '@/components/confirm-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScanOverview from '$lib/components/scans/results/scan-overview.svelte';
	import WebAssetsTable from '$lib/components/scans/results/web-assets-table.svelte';
	import IpsTable from '$lib/components/scans/results/ips-table.svelte';
	import ServicesTable from '$lib/components/scans/results/services-table.svelte';
	import EndpointsTable from '$lib/components/scans/results/endpoints-table.svelte';
	import VulnerabilitiesTable from '$lib/components/scans/results/vulnerabilities-table.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import {
		durationLabel,
		isLiveStatus,
		scanStatusIcon,
		SCAN_STATUS_LABEL,
		SCAN_POLL_MS
	} from '$lib/utilities/scan-status';
	import { emptyQuery, type WebAssetQuery } from '$lib/utilities/scan-insights';
	import { emptyIpQuery, type IpQuery } from '$lib/utilities/ip-groups';
	import { emptyServiceQuery, type ServiceQuery } from '$lib/utilities/services';
	import { emptyEndpointQuery, type EndpointQuery } from '$lib/utilities/endpoints';
	import { emptyVulnQuery, type VulnQuery } from '$lib/utilities/vulns';
	import { targetTypeLabel } from '$lib/types/scan-engine';
	import { TARGET_TYPE_ICONS, type IconComponent } from '$lib/config/icons';
	import { RESULT_TABS, SURFACE_ORDER } from '$lib/config/surface';
	import { plannedStages } from '$lib/utilities/scan-progress';
	import type { TargetType } from '$lib/types/target';
	import type { ScanRead, ScanActivityRead, ScanCommandRead } from '$lib/types/scan';
	import { ROUTES } from '$lib/config/routes';
	import GenerateReportDialog from '$lib/components/reports/generate-dialog.svelte';
	import { NOW_TICK_MS } from '$lib/constants';

	const TABS = ['overview', ...RESULT_TABS] as const;
	type TabKey = (typeof TABS)[number];
	const TAB_DEFS: { key: TabKey; label: string; icon: IconComponent }[] = [
		{ key: 'overview', label: 'Overview', icon: LayoutDashboard },
		...SURFACE_ORDER.map((s) => ({ key: s.tab as TabKey, label: s.label, icon: s.icon }))
	];
	const HISTORY_SIZE = 12;
	const STATUS_TEXT: Record<string, string> = {
		running: 'text-info',
		completed: 'text-success',
		failed: 'text-destructive'
	};

	const scanId = $derived(page.params.id ?? '');

	let scan = $state<ScanRead | null>(null);
	let activities = $state<ScanActivityRead[]>([]);
	let commands = $state<ScanCommandRead[]>([]);
	let history = $state<ScanRead[]>([]);
	let historyLoaded = $state(false);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showRescan = $state(false);
	let cancelOpen = $state(false);
	let reportOpen = $state(false);
	let cancelling = $state(false);
	let headerEl = $state<HTMLElement | null>(null);
	let condensed = $state(false);
	let tabsHeight = $state(0);
	let refreshTimer: ReturnType<typeof setTimeout> | null = null;
	let now = $state(Date.now());
	const initialSearch = (key: string) => page.url.searchParams.get(key) ?? '';
	let webQuery = $state<WebAssetQuery>({ ...emptyQuery(), search: initialSearch('q') });
	let ipQuery = $state<IpQuery>({ ...emptyIpQuery(), search: initialSearch('ip_q') });
	let serviceQuery = $state<ServiceQuery>({
		...emptyServiceQuery(),
		search: initialSearch('svc_q')
	});
	let vulnQuery = $state<VulnQuery>({ ...emptyVulnQuery(), search: initialSearch('vuln_q') });
	let endpointQuery = $state<EndpointQuery>({
		...emptyEndpointQuery(),
		search: initialSearch('ep_q')
	});

	const initialTab = page.url.searchParams.get('tab');
	let activeTab = $state<TabKey>(
		initialTab && (TABS as readonly string[]).includes(initialTab)
			? (initialTab as TabKey)
			: 'overview'
	);

	function setTab(v: string) {
		activeTab = v as TabKey;
		try {
			const sp = new SvelteURLSearchParams(location.search);
			sp.set('tab', v);
			replaceState(`?${sp.toString()}`, page.state);
		} catch {
			// ignore — URL state is best-effort
		}
	}

	function applyFilter(search: string) {
		webQuery = { ...emptyQuery(), search };
		setTab('web-assets');
	}

	function openTab(tab: string, filter?: string) {
		if (!filter) {
			setTab(tab);
			return;
		}
		if (tab === 'ips') {
			ipQuery = { ...emptyIpQuery(), search: filter };
			setTab('ips');
			return;
		}
		if (tab === 'endpoints') {
			endpointQuery = { ...emptyEndpointQuery(), search: filter };
			setTab('endpoints');
			return;
		}
		if (tab === 'services') {
			serviceQuery = { ...emptyServiceQuery(), search: filter };
			setTab('services');
			return;
		}
		if (tab === 'vulnerabilities') {
			vulnQuery = { ...emptyVulnQuery(), search: filter };
			setTab('vulnerabilities');
			return;
		}
		applyFilter(filter);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		const n = Number(e.key);
		if (n >= 1 && n <= visibleTabs.length) setTab(visibleTabs[n - 1].key);
	}

	async function copyTarget() {
		if (!scan) return;
		const ok = await writeClipboard(scan.execution_config.target_value);
		if (ok) toast.success('Copied');
	}

	$effect(() => {
		if (!scan || !isLiveStatus(scan.status)) return;
		const t = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		return () => clearInterval(t);
	});

	$effect(() => {
		const el = headerEl;
		if (!el) return;
		const io = new IntersectionObserver(([entry]) => (condensed = !entry.isIntersecting), {
			threshold: 0
		});
		io.observe(el);
		return () => io.disconnect();
	});

	let live = $derived(!!scan && isLiveStatus(scan.status));
	let focused = $derived(scan?.scope === 'focused');
	let seedNoun = $derived(
		(scan?.seed_count ?? 0) === 1 ? '1 asset' : `${scan?.seed_count ?? 0} assets`
	);
	let shouldPoll = $derived(live && !sseStore.isConnected);
	let TargetIcon = $derived(
		scan ? (TARGET_TYPE_ICONS[scan.execution_config.target_type as TargetType] ?? Globe) : Globe
	);
	let StatusIcon = $derived(scan ? scanStatusIcon(scan.status) : Globe);
	let previous = $derived.by<ScanRead | null>(() => {
		if (!scan) return null;
		const at = new Date(scan.started_at ?? scan.created_at).getTime();
		return (
			history.find(
				(s) =>
					s.id !== scan!.id &&
					s.status === 'completed' &&
					new Date(s.started_at ?? s.created_at).getTime() < at
			) ?? null
		);
	});
	let previousDuration = $derived.by<number | null>(() => {
		if (!scan) return null;
		const done = history.filter(
			(s) => s.id !== scan!.id && s.status === 'completed' && s.duration_seconds != null
		);
		return done.find((s) => s.engine_name === scan!.engine_name)?.duration_seconds ?? null;
	});
	let ipsTotal = $state<number | null>(null);
	let servicesTotal = $state<number | null>(null);
	let endpointsTotal = $state<number | null>(null);
	let vulnsTotal = $state<number | null>(null);
	let tabCounts = $derived<Record<TabKey, number | null>>({
		overview: null,
		'web-assets': scan?.subdomains_found ?? 0,
		endpoints: endpointsTotal ?? scan?.endpoints_found ?? 0,
		services: servicesTotal ?? scan?.open_ports_found ?? 0,
		ips: ipsTotal ?? scan?.ips_found ?? 0,
		vulnerabilities: vulnsTotal ?? scan?.vulnerabilities_found ?? 0
	});
	let plannedKinds = $derived(
		new Set(scan ? plannedStages(scan, engineCatalogStore.stages).flatMap((st) => st.produces) : [])
	);
	// a result tab earns its place with rows, or with a planned producer while the scan is live
	let visibleTabs = $derived(
		TAB_DEFS.filter((t) => {
			if (t.key === 'overview') return true;
			if ((tabCounts[t.key] ?? 0) > 0) return true;
			const spec = SURFACE_ORDER.find((sp) => sp.tab === t.key);
			return live && !!spec && spec.kinds.some((k) => plannedKinds.has(k));
		})
	);
	$effect(() => {
		if (scan && !loading && !visibleTabs.some((t) => t.key === activeTab)) setTab('overview');
	});
	let timing = $derived.by(() => {
		if (!scan) return '';
		if (scan.status === 'pending') return `created ${relativeTime(scan.created_at)}`;
		if (live)
			return `started ${relativeTime(scan.started_at)} · ${durationLabel(scan, now)} elapsed`;
		const end = scan.completed_at ? relativeTime(scan.completed_at) : relativeTime(scan.started_at);
		return `${end} · took ${durationLabel(scan, now)}`;
	});

	// seeded so the first mount keeps the queries the URL asked for
	let lastScanId = page.params.id ?? '';
	$effect(() => {
		if (scanId && scanId !== lastScanId) {
			lastScanId = scanId;
			untrack(() => {
				webQuery = emptyQuery();
				ipQuery = emptyIpQuery();
				serviceQuery = emptyServiceQuery();
				endpointQuery = emptyEndpointQuery();
				vulnQuery = emptyVulnQuery();
				history = [];
				historyLoaded = false;
			});
		}
	});

	async function loadPipeline(projectId: string) {
		try {
			[activities, commands] = await Promise.all([
				scansApi.activities(scanId, projectId),
				scansApi.commands(scanId, projectId)
			]);
		} catch {
			// pipeline is supplementary — leave prior values on failure
		}
	}

	async function loadHistory(projectId: string, targetId: string) {
		try {
			const res = await scansApi.list(projectId, {
				target_id: targetId,
				size: HISTORY_SIZE,
				sort_by: 'started',
				sort_dir: 'desc'
			});
			history = res.items;
		} catch {
			// history is supplementary
		} finally {
			historyLoaded = true;
		}
	}

	let lastStatus: string | null = null;
	async function load(silent = false) {
		const project = projectsStore.activeProject;
		if (!project || !scanId) return;
		if (!silent) loading = true;
		error = null;
		try {
			scan = await scansApi.get(scanId, project.id);
			if (!silent) breadcrumbStore.set(scanId, `${scan.execution_config.target_value} scan`);
			const statusChanged = scan.status !== lastStatus;
			lastStatus = scan.status;
			await Promise.all([
				loadPipeline(project.id),
				statusChanged || !historyLoaded ? loadHistory(project.id, scan.target_id) : null
			]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load scan';
		} finally {
			if (!silent) loading = false;
		}
	}

	function scheduleRefresh() {
		if (refreshTimer) return;
		refreshTimer = setTimeout(() => {
			refreshTimer = null;
			load(true);
		}, 600);
	}

	async function confirmCancel() {
		if (!scan) return;
		cancelling = true;
		const ok = await liveScans.cancel(scan);
		cancelling = false;
		cancelOpen = false;
		if (ok) {
			toast.success('Scan cancelled');
			load(true);
		} else toast.error('Could not cancel the scan');
	}

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (project && id) untrack(() => load());
	});

	$effect(() => {
		if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (!project || !id) return;
		return sseStore.on<ScanEvent>(SSEChannel.project(project.id), SSEEventType.SCAN, (data) => {
			if (data.scan_id === id) scheduleRefresh();
		});
	});

	$effect(() => {
		if (!shouldPoll) return;
		const t = setInterval(() => load(true), SCAN_POLL_MS);
		return () => clearInterval(t);
	});

	onDestroy(() => {
		if (refreshTimer) clearTimeout(refreshTimer);
		if (scanId) breadcrumbStore.remove(scanId);
	});

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let targetHref = $derived(scan ? ROUTES.target(scan.target_id) : ROUTES.scans);
	let reportsHref = $derived(scan ? ROUTES.reportsForScan(scan.id) : ROUTES.reports());
</script>

<svelte:window onkeydown={onKeydown} />

<div class="flex w-full flex-col gap-5 px-4 py-4 md:px-6">
	<a
		href={focused && scan?.parent_scan_id ? ROUTES.scan(scan.parent_scan_id) : ROUTES.scans}
		class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="size-3.5" />
		{focused && scan?.parent_scan_id ? 'The run this was seeded from' : 'Scans'}
	</a>

	{#if loading && !scan}
		<Skeleton class="h-16 w-2/3" />
		<Skeleton class="h-10 w-96" />
		<Skeleton class="h-96 w-full" />
	{:else if error}
		<Empty.Root class="rounded-lg border border-dashed py-20">
			<Empty.Header>
				<Empty.Title class="text-sm">Could not load scan</Empty.Title>
				<Empty.Description>{error}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" onclick={() => load()}>Retry</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if scan}
		<header bind:this={headerEl} class="flex flex-wrap items-start justify-between gap-4">
			<div class="flex min-w-0 items-start gap-3">
				<div
					class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/40"
				>
					<TargetIcon class="size-5 text-muted-foreground" />
				</div>
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<h1 class="truncate font-mono text-xl font-medium">
							{scan.execution_config.target_value}
						</h1>
						<Badge variant="outline" class="font-normal text-muted-foreground">
							{targetTypeLabel(scan.execution_config.target_type)}
						</Badge>
					</div>
					<p
						class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground"
					>
						<ScanStatusBadge status={scan.status} class="h-5" />
						{#if focused}
							<Badge variant="info" class="h-5 font-normal">Focused</Badge>
						{/if}
						<span>{timing}</span>
						<span aria-hidden="true">·</span>
						<span>{scan.engine_name}</span>
						<span aria-hidden="true">·</span>
						<span>{scan.context_name ?? 'engine defaults'}</span>
					</p>
				</div>
			</div>
			<div class="flex items-center gap-2">
				{#if live}
					<Button variant="outline" size="sm" class="gap-1.5" onclick={() => (cancelOpen = true)}>
						<Ban class="size-3.5" />
						Cancel
					</Button>
				{:else}
					<Button variant="outline" size="sm" class="gap-1.5" onclick={() => (reportOpen = true)}>
						<FileText class="size-3.5" />
						Report
					</Button>
					<Button size="sm" class="gap-1.5" onclick={() => (showRescan = true)}>
						<Play class="size-3.5" />
						Re-scan
					</Button>
				{/if}
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button {...props} variant="outline" size="icon-sm" aria-label="More actions">
								<Ellipsis class="size-4" />
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-48">
						<DropdownMenu.Item onclick={() => load()}>
							<RefreshCw class="size-4" />
							Refresh
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={copyTarget}>
							<Copy class="size-4" />
							Copy target
						</DropdownMenu.Item>
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={reportsHref}>
									<FileText class="size-4" />
									Reports for this run
								</a>
							{/snippet}
						</DropdownMenu.Item>
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={targetHref}>
									<ExternalLink class="size-4" />
									Open target
								</a>
							{/snippet}
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		</header>

		{#if focused}
			<p class="rounded-md border border-info/30 bg-info/5 p-3 text-sm">
				<span class="font-medium">A focused scan.</span>
				<span class="text-muted-foreground">
					Its counts describe the {seedNoun} it was given, not this target's surface — the target summary
					and dashboard read from full runs.
				</span>
			</p>
		{/if}

		{#if scan.error && scan.status === 'failed'}
			<p
				class="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
			>
				{scan.error}
			</p>
		{/if}

		<Tabs.Root value={activeTab} onValueChange={setTab} style="--scan-tabs-h: {tabsHeight}px">
			<div
				bind:clientHeight={tabsHeight}
				class="sticky top-0 z-30 -mx-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:-mx-6 md:px-6"
			>
				<div class="flex items-center gap-4">
					{#if condensed}
						<div
							class="hidden shrink-0 items-center gap-2 border-r border-border py-2 pr-4 sm:flex"
						>
							<span class="font-mono text-sm">{scan.execution_config.target_value}</span>
							<StatusIcon
								class="size-3.5 {STATUS_TEXT[scan.status] ??
									'text-muted-foreground'} {scan.status === 'running' ? 'animate-spin' : ''}"
								aria-label={SCAN_STATUS_LABEL[scan.status]}
							/>
						</div>
					{/if}
					<Tabs.List class="h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
						{#each visibleTabs as t, i (t.key)}
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
														: 'text-muted-foreground'}">{n.toLocaleString()}</span
												>
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
			</div>

			<Tabs.Content value="overview" class="mt-6">
				{#key scan.id}
					<ScanOverview
						{scan}
						scanId={scan.id}
						{projectId}
						{activities}
						{commands}
						{history}
						{historyLoaded}
						{previous}
						{previousDuration}
						{now}
						active={activeTab === 'overview'}
						onFilter={applyFilter}
						onTab={openTab}
						onRescan={() => (showRescan = true)}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="web-assets" class="mt-6">
				{#key scan.id}
					<WebAssetsTable
						scanId={scan.id}
						targetId={scan.target_id}
						targetType={scan.execution_config.target_type}
						{projectId}
						apex={scan.execution_config.target_value}
						active={activeTab === 'web-assets'}
						onTab={openTab}
						bind:query={webQuery}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="endpoints" class="mt-6">
				{#key scan.id}
					<EndpointsTable
						scanId={scan.id}
						{projectId}
						active={activeTab === 'endpoints'}
						onTab={openTab}
						onScanTotal={(n) => (endpointsTotal = n)}
						bind:query={endpointQuery}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="services" class="mt-6">
				{#key scan.id}
					<ServicesTable
						scanId={scan.id}
						targetId={scan.target_id}
						targetType={scan.execution_config.target_type}
						{projectId}
						active={activeTab === 'services'}
						onTab={openTab}
						onScanTotal={(n) => (servicesTotal = n)}
						bind:query={serviceQuery}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="ips" class="mt-6">
				{#key scan.id}
					<IpsTable
						scanId={scan.id}
						targetId={scan.target_id}
						targetType={scan.execution_config.target_type}
						{projectId}
						active={activeTab === 'ips'}
						onTab={openTab}
						onScanTotal={(n) => (ipsTotal = n)}
						bind:query={ipQuery}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="vulnerabilities" class="mt-6">
				{#key scan.id}
					<VulnerabilitiesTable
						scanId={scan.id}
						targetId={scan.target_id}
						targetType={scan.execution_config.target_type}
						active={activeTab === 'vulnerabilities'}
						onTab={openTab}
						onScanTotal={(n) => (vulnsTotal = n)}
						bind:query={vulnQuery}
					/>
				{/key}
			</Tabs.Content>
		</Tabs.Root>
	{/if}
</div>

{#if scan}
	<GenerateReportDialog
		bind:open={reportOpen}
		projectId={scan.project_id}
		scanId={scan.id}
		subject={scan.execution_config.target_value}
	/>
	<LaunchDialog
		bind:open={showRescan}
		targetId={scan.target_id}
		rerun={scan}
		onClose={() => (showRescan = false)}
	/>
	<ConfirmDialog
		bind:open={cancelOpen}
		title="Cancel this scan?"
		description="The scan will stop queuing further work and be marked cancelled."
		confirmLabel="Cancel scan"
		destructive
		loading={cancelling}
		loadingLabel="Cancelling…"
		onOpenChange={(o) => (cancelOpen = o)}
		onConfirm={confirmCancel}
	/>
{/if}
