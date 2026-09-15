<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Globe from '@lucide/svelte/icons/globe';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import Pause from '@lucide/svelte/icons/pause';
	import Copy from '@lucide/svelte/icons/copy';
	import FileText from '@lucide/svelte/icons/file-text';
	import FileDown from '@lucide/svelte/icons/file-down';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import GitCompareArrows from '@lucide/svelte/icons/git-compare-arrows';

	import { scansApi } from '$lib/api/scans';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { exportsStore } from '$lib/stores/exports.svelte';
	import { BUNDLE } from '$lib/config/exports';
	import type { ExportRead } from '$lib/types/export';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { SCAN_EVENT_KIND, SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ScanEvent } from '$lib/types/sse';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tabs from '$lib/components/ui/tabs';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Kbd } from '$lib/components/ui/kbd';
	import ScanStatusBadge from '@/components/scan-status-badge.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ConfirmDialog from '@/components/confirm-dialog.svelte';
	import EmptyState from '@/components/empty-state.svelte';
	import LoadingButton from '@/components/loading-button.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScanOverview from '$lib/components/scans/results/scan-overview.svelte';
	import WebAssetsTable from '$lib/components/scans/results/web-assets-table.svelte';
	import IpsTable from '$lib/components/scans/results/ips-table.svelte';
	import ServicesTable from '$lib/components/scans/results/services-table.svelte';
	import EndpointsTable from '$lib/components/scans/results/endpoints-table.svelte';
	import VulnerabilitiesTable from '$lib/components/scans/results/vulnerabilities-table.svelte';
	import SoftwareTable from '$lib/components/scans/results/software-table.svelte';
	import SecretsTable from '$lib/components/scans/results/secrets-table.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import {
		durationLabel,
		isLiveStatus,
		isOpenStatus,
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
	import { TARGET_TYPE_ICONS } from '$lib/config/icons';
	import { SURFACE, SURFACE_ORDER, SurfaceDimension, type SurfaceSpec } from '$lib/config/surface';
	import { NOTES_TAB, SCAN_TABS, SCAN_TAB_DEFS, type ScanTab } from '$lib/config/scan-tabs';
	import { scanTabs } from '$lib/stores/scan-tabs.svelte';
	import TabMenu from '$lib/components/scans/results/tab-menu.svelte';
	import { INTEREST_TAB } from '$lib/config/interest';
	import { CORRELATION_TAB } from '$lib/config/correlation';
	import CorrelationTab from '$lib/components/scans/results/correlation/correlation-tab.svelte';
	import NotePanel from '$lib/components/notes/note-panel.svelte';
	import InterestingTable from '$lib/components/scans/results/interesting/interesting-table.svelte';
	import { plannedStages } from '$lib/utilities/scan-progress';
	import type { TargetType } from '$lib/types/target';
	import { SCAN_COUNT_COLUMNS } from '$lib/types/scan';
	import type { ScanRead, ScanActivityRead, ScanCommandRead } from '$lib/types/scan';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { REFUSAL } from '$lib/config/compare';
	import GenerateReportDialog from '$lib/components/reports/generate-dialog.svelte';
	import { NOW_TICK_MS } from '$lib/constants';

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
	let pausing = $state(false);
	let resuming = $state(false);
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

	let resultTicks = $state<Record<string, number>>({});
	let liveTick = $derived(Object.values(resultTicks).reduce((a, b) => a + b, 0));

	function applyLiveCounts(counts: Record<string, number> | undefined) {
		if (!scan || !counts) return;
		for (const column of Object.values(SCAN_COUNT_COLUMNS)) {
			const value = counts[column];
			if (typeof value === 'number') scan[column] = value;
		}
	}

	function countsOf(run: ScanRead | null): Record<string, number> {
		if (!run) return {};
		return Object.fromEntries(
			Object.values(SCAN_COUNT_COLUMNS).map((c) => [c, (run[c] as number) ?? 0])
		);
	}

	function bumpChangedDimensions(before: Record<string, number>, after: ScanRead) {
		if (!Object.keys(before).length) return;
		for (const spec of SURFACE_ORDER) {
			if (!spec.countColumns.some((c) => before[c] !== ((after[c] as number) ?? 0))) continue;
			resultTicks[spec.key] = (resultTicks[spec.key] ?? 0) + 1;
			if (spec.key === SurfaceDimension.WEB_ASSETS)
				resultTicks[INTEREST_TAB] = (resultTicks[INTEREST_TAB] ?? 0) + 1;
		}
	}

	const initialTab = page.url.searchParams.get('tab');
	let activeTab = $state<ScanTab>(
		initialTab && (SCAN_TABS as readonly string[]).includes(initialTab)
			? (initialTab as ScanTab)
			: 'overview'
	);

	function setTab(v: string) {
		activeTab = v as ScanTab;
		try {
			const sp = new SvelteURLSearchParams(location.search);
			sp.set('tab', v);
			replaceState(`?${sp.toString()}`, page.state);
		} catch {
			// ignore
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
	let paused = $derived(scan?.status === 'paused');
	let unfinished = $derived(!!scan && isOpenStatus(scan.status));
	let runningStages = $derived(activities.filter((a) => a.status === 'running').length);
	let pauseNote = $derived(
		runningStages
			? `${runningStages} running ${runningStages === 1 ? 'stage' : 'stages'} stop and run again from the start on resume.`
			: 'The scan stops before its next stage.'
	);
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
	let comparable = $derived.by<ScanRead | null>(() => {
		if (!scan || unfinished) return null;
		const at = new Date(scan.started_at ?? scan.created_at).getTime();
		return (
			history.find(
				(s) =>
					s.id !== scan!.id &&
					s.scope === scan!.scope &&
					!isOpenStatus(s.status) &&
					new Date(s.started_at ?? s.created_at).getTime() < at
			) ?? null
		);
	});
	let compareReason = $derived.by<string>(() => {
		if (!scan || comparable) return '';
		if (unfinished) return REFUSAL.UNFINISHED;
		if (!historyLoaded) return '';
		return focused
			? REFUSAL.FOCUSED_AGAINST_FULL
			: `First run of ${scan.execution_config.target_value}. ${REFUSAL.NO_EARLIER_RUN}`;
	});
	let previousDuration = $derived.by<number | null>(() => {
		if (!scan) return null;
		const done = history.filter(
			(s) => s.id !== scan!.id && s.status === 'completed' && s.duration_seconds != null
		);
		return done.find((s) => s.engine_name === scan!.engine_name)?.duration_seconds ?? null;
	});
	let interestTotal = $state<number | null>(null);
	let correlationTotal = $state<number | null>(null);
	let ipsTotal = $state<number | null>(null);
	let servicesTotal = $state<number | null>(null);
	let endpointsTotal = $state<number | null>(null);
	let vulnsTotal = $state<number | null>(null);
	let notesTotal = $state<number | null>(null);
	let softwareTotal = $state<number | null>(null);
	let softwareSearch = $state('');
	let secretsTotal = $state<number | null>(null);
	let secretSearch = $state('');
	let tabCounts = $derived<Record<ScanTab, number | null>>({
		overview: null,
		[INTEREST_TAB]: interestTotal,
		'web-assets': scan?.subdomains_found ?? 0,
		endpoints: endpointsTotal ?? scan?.endpoints_found ?? 0,
		services: servicesTotal ?? scan?.open_ports_found ?? 0,
		ips: ipsTotal ?? scan?.ips_found ?? 0,
		vulnerabilities: vulnsTotal ?? scan?.vulnerabilities_found ?? 0,
		software: softwareTotal,
		secrets: secretsTotal,
		[CORRELATION_TAB]: correlationTotal,
		[NOTES_TAB]: notesTotal
	});
	let plannedKinds = $derived(
		new Set(scan ? plannedStages(scan, engineCatalogStore.stages).flatMap((st) => st.produces) : [])
	);
	function dimensionOn(spec: SurfaceSpec): boolean {
		if (spec.countColumns.some((c) => ((scan?.[c] as number) ?? 0) > 0)) return true;
		return spec.kinds.some((k) => plannedKinds.has(k));
	}
	let defaultTabs = $derived(
		new Set(
			SCAN_TAB_DEFS.filter((t) => {
				if (t.key === 'overview' || t.key === NOTES_TAB) return true;
				if (t.key === CORRELATION_TAB) return (scan?.subdomains_found ?? 0) >= 2;
				if (t.key === INTEREST_TAB) return dimensionOn(SURFACE[SurfaceDimension.WEB_ASSETS]);
				const spec = SURFACE_ORDER.find((sp) => sp.tab === t.key);
				return !!spec && dimensionOn(spec);
			}).map((t) => t.key)
		)
	);
	// a tab offered once stays offered
	let offered = new SvelteSet<string>();
	let offeredFor = $state('');
	$effect(() => {
		const id = scanId;
		const keys = [...defaultTabs];
		untrack(() => {
			if (offeredFor !== id) {
				offered.clear();
				offeredFor = id;
			}
			for (const k of keys) offered.add(k);
		});
	});
	function tabOn(key: ScanTab): boolean {
		return scanTabs.visible(key, defaultTabs.has(key) || offered.has(key));
	}
	let visibleTabs = $derived(SCAN_TAB_DEFS.filter((t) => t.key === activeTab || tabOn(t.key)));
	let tabMenuRows = $derived(
		SCAN_TAB_DEFS.map((t) => ({
			...t,
			defaultOn: defaultTabs.has(t.key) || offered.has(t.key),
			count: tabCounts[t.key]
		}))
	);
	function onTabToggle(key: ScanTab, visible: boolean) {
		if (!visible && key === activeTab) setTab('overview');
	}
	function tabSpec(tab: string): SurfaceSpec | undefined {
		if (tab === INTEREST_TAB || tab === CORRELATION_TAB)
			return SURFACE[SurfaceDimension.WEB_ASSETS];
		return SURFACE_ORDER.find((sp) => sp.tab === tab);
	}
	function notScanned(tab: string): boolean {
		const spec = tabSpec(tab);
		return !!spec && !dimensionOn(spec);
	}
	let surfaceLink = $derived.by(() => {
		const spec = SURFACE_ORDER.find((sp) => sp.tab === activeTab);
		if (!spec) return '';
		const search = {
			[SurfaceDimension.WEB_ASSETS]: webQuery.search,
			[SurfaceDimension.ENDPOINTS]: endpointQuery.search,
			[SurfaceDimension.SERVICES]: serviceQuery.search,
			[SurfaceDimension.IPS]: ipQuery.search,
			[SurfaceDimension.VULNERABILITIES]: vulnQuery.search,
			[SurfaceDimension.SOFTWARE]: softwareSearch,
			[SurfaceDimension.SECRETS]: secretSearch
		}[spec.key];
		return ROUTES.surface(spec.tab, search ? { [spec.queryParam]: search } : undefined);
	});
	let timing = $derived.by(() => {
		if (!scan) return '';
		if (scan.status === 'pending') return `created ${relativeTime(scan.created_at)}`;
		if (live)
			return `started ${relativeTime(scan.started_at)} · ${durationLabel(scan, now)} elapsed`;
		const end = scan.completed_at ? relativeTime(scan.completed_at) : relativeTime(scan.started_at);
		return `${end} · took ${durationLabel(scan, now)}`;
	});

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
				resultTicks = {};
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
		} catch {}
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
			// ignore
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
		const before = countsOf(scan);
		try {
			scan = await scansApi.get(scanId, project.id);
			bumpChangedDimensions(before, scan);
			if (!silent) breadcrumbStore.set(scanId, `${scan.execution_config.target_value} scan`);
			const statusChanged = scan.status !== lastStatus;
			lastStatus = scan.status;
			await Promise.all([
				loadPipeline(project.id),
				statusChanged || !historyLoaded ? loadHistory(project.id, scan.target_id) : null
			]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Scan not loaded';
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

	async function pause() {
		if (!scan || pausing) return;
		pausing = true;
		const updated = await liveScans.pause(scan);
		pausing = false;
		if (updated) {
			scan = updated;
			toast.success('Scan paused');
			load(true);
		} else toast.error('Scan not paused');
	}

	async function resume() {
		if (!scan || resuming) return;
		resuming = true;
		const updated = await liveScans.resume(scan);
		resuming = false;
		if (updated) {
			scan = updated;
			toast.success('Scan resumed');
			load(true);
		} else toast.error('Scan not resumed');
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
		} else toast.error('Scan not cancelled');
	}

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (project && id) untrack(() => load());
	});

	$effect(() => {
		if (!engineCatalogStore.hasFetched) untrack(() => engineCatalogStore.fetch());
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (!project || !id) return;
		return sseStore.on<ScanEvent>(SSEChannel.project(project.id), SSEEventType.SCAN, (data) => {
			if (data.scan_id !== id) return;
			if (data.kind === SCAN_EVENT_KIND.RESULTS_FOUND) {
				applyLiveCounts(data.counts);
				const key = data.dimension ?? '';
				if (key) resultTicks[key] = (resultTicks[key] ?? 0) + 1;
				return;
			}
			if (data.kind === SCAN_EVENT_KIND.INTEREST_READY) {
				resultTicks[INTEREST_TAB] = (resultTicks[INTEREST_TAB] ?? 0) + 1;
				return;
			}
			scheduleRefresh();
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
	let bundling = $state(false);

	async function exportEverything() {
		const project = projectsStore.activeProject?.id;
		if (!project || !scan) return;
		bundling = true;
		try {
			await exportsStore.create(
				project,
				{
					dimension: BUNDLE,
					scan_id: scan.id,
					export_format: 'csv'
				},
				(row: ExportRead) => {
					bundling = false;
					if (row.status !== 'completed') {
						toast.error(row.error || 'Export not written.');
						return;
					}
					toast.success(`${row.row_count.toLocaleString()} rows exported`);
					window.location.href = exportsStore.downloadUrl(row.id);
				}
			);
			toast.success('Export started');
		} catch (e) {
			bundling = false;
			toast.error(e instanceof Error ? e.message : 'Export not started.');
		}
	}
</script>

<svelte:head
	><title>{scan ? `${scan.execution_config.target_value} scan` : routeLabels.scans} · reNgine</title
	></svelte:head
>

<svelte:window onkeydown={onKeydown} />

<div class="flex w-full flex-col gap-5 px-4 py-4 md:px-6">
	<a
		href={focused && scan?.parent_scan_id ? ROUTES.scan(scan.parent_scan_id) : ROUTES.scans}
		class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="size-3.5" />
		{focused && scan?.parent_scan_id ? 'Parent run' : 'Scans'}
	</a>

	{#if loading && !scan}
		<Skeleton class="h-16 w-2/3" />
		<Skeleton class="h-10 w-96" />
		<Skeleton class="h-96 w-full" />
	{:else if error}
		<Empty.Root class="rounded-lg border border-dashed py-20">
			<Empty.Header>
				<Empty.Title class="text-sm">Scan not loaded</Empty.Title>
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
					<Hint text={pauseNote}>
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<LoadingButton
									variant="outline"
									size="sm"
									class="gap-1.5"
									loading={pausing}
									loadingLabel="Pausing…"
									onclick={() => pause()}
								>
									<Pause class="size-3.5" />
									Pause
								</LoadingButton>
							</span>
						{/snippet}
					</Hint>
					<Button variant="outline" size="sm" class="gap-1.5" onclick={() => (cancelOpen = true)}>
						<Ban class="size-3.5" />
						Cancel
					</Button>
				{:else if paused}
					<LoadingButton
						size="sm"
						class="gap-1.5"
						loading={resuming}
						loadingLabel="Resuming…"
						onclick={() => resume()}
					>
						<Play class="size-3.5" />
						Resume
					</LoadingButton>
					<Button variant="outline" size="sm" class="gap-1.5" onclick={() => (cancelOpen = true)}>
						<Ban class="size-3.5" />
						Cancel
					</Button>
				{:else}
					{#if comparable}
						<Button
							variant="outline"
							size="sm"
							class="gap-1.5"
							href={ROUTES.compare(scan.id, comparable.id)}
						>
							<GitCompareArrows class="size-3.5" />
							Compare
						</Button>
					{:else if compareReason}
						<Hint text={compareReason}>
							{#snippet child(props)}
								<span {...props} class="inline-flex">
									<Button
										variant="outline"
										size="sm"
										class="gap-1.5"
										disabled
										aria-label="Compare. {compareReason}"
									>
										<GitCompareArrows class="size-3.5" />
										Compare
									</Button>
								</span>
							{/snippet}
						</Hint>
					{/if}
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
						<DropdownMenu.Item disabled={bundling} onclick={exportEverything}>
							<FileDown class="size-4" />
							Export all dimensions
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
				<span class="font-medium">Focused scan.</span>
				<span class="text-muted-foreground">
					Counts cover the {seedNoun} it was seeded with. The target summary and dashboard read full runs
					only.
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

		{#snippet unscanned(tab: string)}
			{@const spec = tabSpec(tab)}
			<EmptyState icon={spec?.icon} title="Not scanned" class="mt-6" />
		{/snippet}

		{#snippet tabFailed(err: unknown, reset: () => void)}
			<Empty.Root class="rounded-lg border border-dashed py-20">
				<Empty.Header>
					<Empty.Title class="text-sm">Tab not rendered</Empty.Title>
					<Empty.Description>{err instanceof Error ? err.message : String(err)}</Empty.Description>
				</Empty.Header>
				<Empty.Content>
					<Button size="sm" variant="outline" onclick={() => reset()}>Retry</Button>
				</Empty.Content>
			</Empty.Root>
		{/snippet}

		<Tabs.Root value={activeTab} onValueChange={setTab} style="--scan-tabs-h: {tabsHeight}px">
			<div
				bind:clientHeight={tabsHeight}
				class="sticky top-0 z-30 -mx-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:-mx-6 md:px-6"
			>
				<div class="flex items-center gap-2">
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
					<ScrollArea orientation="horizontal" class="min-w-0 flex-1" scrollbarXClasses="h-1">
						<Tabs.List class="h-auto w-max justify-start gap-0 rounded-none bg-transparent p-0">
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
					</ScrollArea>
					<TabMenu rows={tabMenuRows} onToggle={onTabToggle} />
					{#if surfaceLink}
						<a
							href={surfaceLink}
							class="hidden shrink-0 items-center gap-1 py-2.5 pl-2 text-xs whitespace-nowrap text-muted-foreground hover:text-foreground hover:underline sm:flex"
						>
							Across all targets
							<ArrowUpRight class="size-3.5" />
						</a>
					{/if}
				</div>
			</div>

			<Tabs.Content value="overview" class="mt-6">
				<svelte:boundary failed={tabFailed}>
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
							revision={liveTick}
							onFilter={applyFilter}
							onTab={openTab}
							onRescan={() => (showRescan = true)}
						/>
					{/key}
				</svelte:boundary>
			</Tabs.Content>

			<Tabs.Content value={INTEREST_TAB} class="mt-6">
				{#if notScanned(INTEREST_TAB)}
					{@render unscanned(INTEREST_TAB)}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<InterestingTable
								scanId={scan.id}
								{projectId}
								active={activeTab === INTEREST_TAB}
								revision={resultTicks[INTEREST_TAB] ?? 0}
								onTab={openTab}
								onTotal={(n) => (interestTotal = n)}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value={CORRELATION_TAB} class="mt-6">
				{#if notScanned(CORRELATION_TAB)}
					{@render unscanned(CORRELATION_TAB)}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<CorrelationTab
								scanId={scan.id}
								{projectId}
								active={activeTab === CORRELATION_TAB}
								revision={resultTicks[SurfaceDimension.WEB_ASSETS] ?? 0}
								onTab={openTab}
								onTotal={(n) => (correlationTotal = n)}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="web-assets" class="mt-6">
				{#if notScanned('web-assets')}
					{@render unscanned('web-assets')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<WebAssetsTable
								scanId={scan.id}
								targetType={scan.execution_config.target_type}
								{projectId}
								apex={scan.execution_config.target_value}
								active={activeTab === 'web-assets'}
								revision={resultTicks[SurfaceDimension.WEB_ASSETS] ?? 0}
								onTab={openTab}
								bind:query={webQuery}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="endpoints" class="mt-6">
				{#if notScanned('endpoints')}
					{@render unscanned('endpoints')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<EndpointsTable
								scanId={scan.id}
								{projectId}
								active={activeTab === 'endpoints'}
								revision={resultTicks[SurfaceDimension.ENDPOINTS] ?? 0}
								onTab={openTab}
								onScanTotal={(n) => (endpointsTotal = n)}
								bind:query={endpointQuery}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="services" class="mt-6">
				{#if notScanned('services')}
					{@render unscanned('services')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<ServicesTable
								scanId={scan.id}
								targetType={scan.execution_config.target_type}
								{projectId}
								active={activeTab === 'services'}
								revision={resultTicks[SurfaceDimension.SERVICES] ?? 0}
								onTab={openTab}
								onScanTotal={(n) => (servicesTotal = n)}
								bind:query={serviceQuery}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="ips" class="mt-6">
				{#if notScanned('ips')}
					{@render unscanned('ips')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<IpsTable
								scanId={scan.id}
								targetType={scan.execution_config.target_type}
								{projectId}
								active={activeTab === 'ips'}
								revision={resultTicks[SurfaceDimension.IPS] ?? 0}
								onTab={openTab}
								onScanTotal={(n) => (ipsTotal = n)}
								bind:query={ipQuery}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value={NOTES_TAB} class="mt-6">
				<svelte:boundary failed={tabFailed}>
					{#key scan.id}
						<div class="overflow-hidden rounded-xl border bg-card">
							<NotePanel
								anchor={{ targetId: scan.target_id, scanId: scan.id }}
								filter={{ scan_id: scan.id }}
								emptyTitle="No notes on this run"
								emptyDescription="Add a note from one of its assets."
								onCount={(n) => (notesTotal = n)}
							/>
						</div>
					{/key}
				</svelte:boundary>
			</Tabs.Content>

			<Tabs.Content value="vulnerabilities" class="mt-6">
				{#if notScanned('vulnerabilities')}
					{@render unscanned('vulnerabilities')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<VulnerabilitiesTable
								scanId={scan.id}
								targetType={scan.execution_config.target_type}
								active={activeTab === 'vulnerabilities'}
								revision={resultTicks[SurfaceDimension.VULNERABILITIES] ?? 0}
								onTab={openTab}
								onScanTotal={(n) => (vulnsTotal = n)}
								bind:query={vulnQuery}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="software" class="mt-6">
				{#if notScanned('software')}
					{@render unscanned('software')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<SoftwareTable
								scanId={scan.id}
								projectId={scan.project_id}
								active={activeTab === 'software'}
								revision={resultTicks[SurfaceDimension.SOFTWARE] ?? 0}
								onScanTotal={(n) => (softwareTotal = n)}
							/>
						{/key}
					</svelte:boundary>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="secrets" class="mt-6">
				{#if notScanned('secrets')}
					{@render unscanned('secrets')}
				{:else}
					<svelte:boundary failed={tabFailed}>
						{#key scan.id}
							<SecretsTable
								scanId={scan.id}
								projectId={scan.project_id}
								active={activeTab === 'secrets'}
								revision={resultTicks[SurfaceDimension.SECRETS] ?? 0}
								onScanTotal={(n) => (secretsTotal = n)}
							/>
						{/key}
					</svelte:boundary>
				{/if}
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
		title="Cancel scan"
		description="The scan is marked cancelled. Finished stages keep their results."
		confirmLabel="Cancel scan"
		destructive
		loading={cancelling}
		loadingLabel="Cancelling…"
		onOpenChange={(o) => (cancelOpen = o)}
		onConfirm={confirmCancel}
	/>
{/if}
