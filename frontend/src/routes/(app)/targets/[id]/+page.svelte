<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
	import FileText from '@lucide/svelte/icons/file-text';
	import Router from '@lucide/svelte/icons/router';
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import NotePanel from '$lib/components/notes/note-panel.svelte';
	import Network from '@lucide/svelte/icons/network';

	import { targetsApi } from '$lib/api/targets';
	import type { ProgramMatch } from '$lib/types/relations';
	import type { TargetEstate } from '$lib/types/estate';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { Capability } from '$lib/config/capabilities';
	import { scansApi } from '$lib/api/scans';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { domainPostureApi } from '$lib/api/domain-posture';
	import { ipsApi, servicesApi, softwareApi } from '$lib/api/scan-results';
	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import { interestApi } from '$lib/api/interest';
	import { usersApi } from '$lib/api/users';
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
	import type { ScanRead, ScanStatus } from '$lib/types/scan';
	import type { HostingComposition } from '$lib/types/hosting';
	import type { InterestPage } from '$lib/types/interest';
	import type { SoftwareCoverage, SoftwareFacets } from '$lib/types/software';
	import type { DashboardCertBucket, DashboardExposure } from '$lib/types/dashboard';
	import type { Facet, HygieneSummary } from '$lib/utilities/scan-insights';
	import type { DomainPostureSummary } from '$lib/types/domain-posture';
	import type { IpFacetSet } from '$lib/utilities/ip-groups';
	import type { ScanExposure } from '$lib/utilities/services';
	import type { ScanVulnerabilities } from '$lib/utilities/vulns';
	import { Button } from '$lib/components/ui/button';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Spinner } from '$lib/components/ui/spinner';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import TargetHeader from '$lib/components/targets/target-detail/target-header.svelte';
	import GenerateReportDialog from '$lib/components/reports/generate-dialog.svelte';
	import TargetHeaderSkeleton from '$lib/components/targets/target-detail/target-header-skeleton.svelte';
	import SurfaceStrip from '$lib/components/targets/target-detail/overview/surface-strip.svelte';
	import FindingsCell from '$lib/components/targets/target-detail/overview/findings-cell.svelte';
	import PostureCell from '$lib/components/targets/target-detail/overview/posture-cell.svelte';
	import HostingCell from '$lib/components/targets/target-detail/overview/hosting-cell.svelte';
	import IdentityCell from '$lib/components/targets/target-detail/overview/identity-cell.svelte';
	import ProgramsCell from '$lib/components/targets/target-detail/overview/programs-cell.svelte';
	import MonitoringCell from '$lib/components/targets/target-detail/overview/monitoring-cell.svelte';
	import SeedsCell from '$lib/components/targets/target-detail/overview/seeds-cell.svelte';
	import EstateTray from '$lib/components/targets/estate-tray.svelte';
	import ActivityCell from '$lib/components/targets/target-detail/overview/activity-cell.svelte';
	import RunsCell from '$lib/components/targets/target-detail/overview/runs-cell.svelte';
	import ReachabilityCell, {
		reachabilityStates
	} from '$lib/components/targets/target-detail/overview/reachability-cell.svelte';
	import GeoCell from '$lib/components/dashboard/geo-cell.svelte';
	import ServicesCell from '$lib/components/dashboard/services-cell.svelte';
	import TechCell from '$lib/components/dashboard/tech-cell.svelte';
	import HygieneCell from '$lib/components/dashboard/hygiene-cell.svelte';
	import DomainPostureCell from '$lib/components/dashboard/domain-posture-cell.svelte';
	import SoftwareCell from '$lib/components/dashboard/software-cell.svelte';
	import CertsCell from '$lib/components/dashboard/certs-cell.svelte';
	import ExposuresCell from '$lib/components/dashboard/exposures-cell.svelte';
	import {
		CERT_FILTER,
		EXPIRING_FILTER
	} from '$lib/components/scans/results/overview/posture-panel.svelte';
	import { buildTargetIntel } from '$lib/components/targets/target-detail/overview/derive';
	import TargetWebAssets from '$lib/components/targets/target-detail/target-web-assets.svelte';
	import DnsTab from '$lib/components/targets/target-detail/dns/dns-tab.svelte';
	import WhoisTab from '$lib/components/targets/target-detail/whois/whois-tab.svelte';
	import BgpTab from '$lib/components/targets/target-detail/bgp/bgp-tab.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import { NOW_TICK_MS } from '$lib/constants';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import { downloadBlob } from '$lib/utilities/download';

	const TABS = ['overview', 'web-assets', 'dns', 'whois', 'bgp', 'notes'] as const;
	type TabKey = (typeof TABS)[number];
	const TAB_DEFS: Record<TabKey, { label: string; icon: IconComponent }> = {
		overview: { label: 'Overview', icon: LayoutDashboard },
		'web-assets': {
			label: SURFACE[SurfaceDimension.WEB_ASSETS].label,
			icon: SURFACE[SurfaceDimension.WEB_ASSETS].icon
		},
		dns: { label: 'DNS', icon: Network },
		whois: { label: 'WHOIS', icon: FileText },
		bgp: { label: 'BGP', icon: Router },
		notes: { label: 'Notes', icon: StickyNote }
	};
	const LEGACY_TABS: Record<string, TabKey> = {
		summary: 'overview',
		intelligence: 'whois',
		scans: 'overview'
	};
	const ENRICHMENT_POLL_MS = 2500;
	const MAX_ENRICHMENT_POLLS = 30;
	const HISTORY_SIZE = 12;
	const EXPOSURE_ROWS = 6;
	const DNS_TYPES = [TargetType.DOMAIN, TargetType.URL];
	const BGP_TYPES = [TargetType.IP, TargetType.IP_RANGE, TargetType.ASN];
	const CERT_BUCKET_KEY: Record<string, string> = {
		expired: 'expired',
		d7: 'week',
		d30: 'month',
		d90: 'quarter',
		ok: 'later'
	};
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	const targetId = $derived(page.params.id ?? '');

	let target = $state<Target | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let showDeleteDialog = $state(false);
	let reportOpen = $state(false);
	let isDeleting = $state(false);
	let showLaunchModal = $state(false);
	let cancelOpen = $state(false);
	let cancelling = $state(false);

	let detail = $state<TargetDetailRead | null>(null);
	let detailLoading = $state(true);
	let detailError = $state<string | null>(null);
	let summary = $state<TargetSummaryRead | null>(null);
	let summaryLoading = $state(true);
	let history = $state<ScanRead[]>([]);
	let historyLoaded = $state(false);
	let programs = $state<ProgramMatch[]>([]);
	let estate = $state<TargetEstate | null>(null);
	let programsLoaded = false;
	let ipFacets = $state<IpFacetSet | null>(null);
	let hosting = $state<HostingComposition | null>(null);
	let tech = $state<Facet[] | null>(null);
	let hygiene = $state<HygieneSummary | null>(null);
	let posture = $state<DomainPostureSummary | null>(null);
	let postureHosts = $state<HygieneSummary | null>(null);
	let certBuckets = $state<DashboardCertBucket[] | null>(null);
	let reach = $state<Record<string, number> | null>(null);
	let exposures = $state<InterestPage | null>(null);
	let exposure = $state<ScanExposure | null>(null);
	let vulns = $state<ScanVulnerabilities | null>(null);
	let software = $state<{ facets: SoftwareFacets; coverage: SoftwareCoverage } | null>(null);
	let extrasLoading = $state(false);
	const notLoaded = new SvelteSet<string>();

	function loaded(section: string) {
		notLoaded.delete(section);
	}
	function notLoadedNow(section: string) {
		notLoaded.add(section);
	}
	let creator = $state<string | null>(null);
	let refreshing = $state<Record<string, boolean>>({});
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let tabsHeight = $state(0);
	let headerEl = $state<HTMLElement | null>(null);
	let condensed = $state(false);
	let now = $state(Date.now());

	let showDns = $derived(!!target && DNS_TYPES.includes(target.target_type));
	let showBgp = $derived(!!target && BGP_TYPES.includes(target.target_type));
	let whoisStatus = $derived(detail?.whois_status ?? target?.whois_status ?? TaskStatus.PENDING);
	let dnsStatus = $derived(detail?.dns_status ?? target?.dns_status ?? TaskStatus.PENDING);
	let bgpStatus = $derived(detail?.bgp_status ?? target?.bgp_status ?? TaskStatus.PENDING);
	let intel = $derived(target ? buildTargetIntel(target, detail) : { rail: [], checks: [] });
	let latest = $derived(summary?.latest_scan ?? null);
	let live = $derived(!!latest && isLiveStatus(latest.status as ScanStatus));
	let run = $derived(live && latest ? liveScans.runFor(latest.id) : undefined);
	let dnsRecords = $derived(
		(detail?.dns?.records ?? []).filter((r) => r.record_type !== 'CDN').length
	);
	const scanFor = (key: SurfaceDimension) =>
		summary?.surface.find((m) => m.key === key && m.covered)?.scan_id ?? null;
	let webScanId = $derived(scanFor(SurfaceDimension.WEB_ASSETS));
	let ipsScanId = $derived(scanFor(SurfaceDimension.IPS));
	let servicesScanId = $derived(scanFor(SurfaceDimension.SERVICES));
	let vulnScanId = $derived(summary?.risk.scan_id ?? null);
	let softwareScanId = $derived(scanFor(SurfaceDimension.SOFTWARE));
	let notesTotal = $state<number | null>(null);
	let tabCounts = $derived<Partial<Record<TabKey, number>>>({
		'web-assets': summary?.inventory_total,
		dns: detail?.dns ? dnsRecords : undefined,
		bgp: detail?.bgp?.announced_prefixes.length || undefined,
		notes: notesTotal ?? undefined
	});
	let bgpHasData = $derived(
		!!detail?.bgp &&
			(!!detail.bgp.as_overview ||
				detail.bgp.announced_prefixes.length > 0 ||
				detail.bgp.network_info.length > 0 ||
				detail.bgp.prefix_overview.length > 0)
	);
	const inFlight = (s: TaskStatus) => s === TaskStatus.PENDING || s === TaskStatus.QUERYING;
	let tabs = $derived(
		TABS.filter((t) => {
			switch (t) {
				case 'web-assets':
					return summaryLoading || live || (summary?.inventory_total ?? 0) > 0;
				case 'dns':
					return showDns && (detailLoading || dnsRecords > 0 || inFlight(dnsStatus));
				case 'whois':
					return detailLoading || !!detail?.whois || inFlight(whoisStatus);
				case 'bgp':
					return showBgp && (detailLoading || bgpHasData || inFlight(bgpStatus));
				default:
					return true;
			}
		})
	);
	let enrichedAt = $derived.by(() => {
		if (!target) return null;
		const times = [
			target.dns_status === TaskStatus.SUCCESS ? target.dns?.queried_at : null,
			target.whois_status === TaskStatus.SUCCESS ? target.whois?.queried_at : null,
			target.bgp_status === TaskStatus.SUCCESS ? target.bgp?.queried_at : null
		]
			.filter((x): x is string => !!x)
			.map((x) => new Date(x).getTime());
		return times.length ? new Date(Math.max(...times)).toISOString() : null;
	});

	// cell visibility
	const SPAN: Record<number, string> = {
		12: 'xl:col-span-12',
		6: 'xl:col-span-6',
		4: 'xl:col-span-4',
		3: 'xl:col-span-3'
	};
	function packed(n: number, perRow = 3): string[] {
		const rows = Math.ceil(n / perRow);
		const base = Math.floor(n / rows);
		const extra = n % rows;
		const out: string[] = [];
		for (let r = 0; r < rows; r++) {
			const k = base + (r < extra ? 1 : 0);
			for (let i = 0; i < k; i++)
				out.push(`col-span-12 ${k > 1 ? 'lg:col-span-6' : ''} ${SPAN[12 / k] ?? ''}`);
		}
		return out;
	}
	let completedRuns = $derived(
		history.filter((s) => s.status === 'completed' && s.scope !== 'focused').length
	);
	let showReach = $derived(!!reach && !!webScanId);
	let webObservedAt = $derived(
		summary?.surface.find((m) => m.key === SurfaceDimension.WEB_ASSETS)?.observed_at ?? null
	);
	let showGeo = $derived((ipFacets?.country.length ?? 0) > 0);
	let showFindings = $derived(!!vulnScanId && !!summary);
	let showPosture = $derived(
		detailLoading || intel.checks.length > 0 || (summary?.sensitive_services ?? 0) > 0
	);
	let showHosting = $derived(!!hosting && hosting.resolving > 0 && !!webScanId);
	let showServices = $derived(!!exposure && exposure.services > 0 && !!servicesScanId);
	let showTech = $derived((tech?.length ?? 0) > 0);
	let showHygiene = $derived((hygiene?.evaluated ?? 0) > 0);
	let showPostureZones = $derived((posture?.evaluated ?? 0) > 0);
	let showSoftware = $derived((software?.facets.product.length ?? 0) > 0);
	let showCerts = $derived(!!certBuckets && certBuckets.some((b) => b.count > 0));
	let showExposures = $derived((exposures?.summary.total ?? 0) > 0);
	let compositionKeys = $derived(
		[
			showGeo && 'geo',
			showHosting && 'hosting',
			showServices && 'services',
			showTech && 'tech',
			showHygiene && 'hygiene',
			showPostureZones && 'domain-posture',
			showSoftware && 'software',
			showCerts && 'certs',
			showExposures && 'exposures'
		].filter((k): k is string => !!k)
	);
	let compositionSpans = $derived(packed(compositionKeys.length));
	let showRuns = $derived(completedRuns >= 2);
	let identityKeys = $derived(
		[
			...intel.rail.map((g) => g.key),
			programs.length ? 'programs' : null,
			summary ? 'monitoring' : null,
			'seeds'
		].filter((k): k is string => !!k)
	);
	let identitySpans = $derived(packed(identityKeys.length));
	let servicesExposure = $derived.by<DashboardExposure | null>(() => {
		const e = exposure;
		if (!e) return null;
		return {
			services: e.services,
			addresses: e.addresses,
			targets: 1,
			sensitive: e.sensitive,
			sensitive_targets: e.sensitive ? 1 : 0,
			non_web: e.non_web_services,
			bands: e.bands.map((b) => ({
				key: b.key,
				label: b.label,
				count: b.count,
				targets: 1,
				query: b.query
			})),
			top: []
		};
	});

	function resolveTab(raw: string | null): TabKey {
		if (!raw) return 'overview';
		const key = (LEGACY_TABS[raw] ?? raw) as TabKey;
		return (TABS as readonly string[]).includes(key) ? key : 'overview';
	}
	let activeTab = $state<TabKey>(resolveTab(page.url.searchParams.get('tab')));

	$effect(() => {
		const fromUrl = resolveTab(page.url.searchParams.get('tab'));
		if (fromUrl !== untrack(() => activeTab)) activeTab = fromUrl;
	});

	$effect(() => {
		if (target && !detailLoading && !summaryLoading && !tabs.includes(activeTab))
			setTab('overview');
	});

	function setTab(value: string) {
		if (!value) return;
		activeTab = value as TabKey;
		if (!browser) return;
		const params = new SvelteURLSearchParams(untrack(() => page.url.searchParams));
		if (value === 'overview') params.delete('tab');
		else params.set('tab', value);
		const query = params.toString();
		try {
			replaceState(query ? `?${query}` : location.pathname, {});
		} catch {
			// history is unavailable during hydration
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		const n = Number(e.key);
		if (n >= 1 && n <= tabs.length) setTab(tabs[n - 1]);
	}

	async function fetchTarget() {
		isLoading = true;
		error = null;
		try {
			target = await targetsApi.get(targetId);
			breadcrumbStore.set(targetId, target.target_value);
		} catch (e) {
			error = errorMessage(e, 'Target not loaded');
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
			detailError = errorMessage(e, 'Enrichment not loaded');
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
			loaded('Surface');
		} catch {
			notLoadedNow('Surface');
		} finally {
			if (!silent) summaryLoading = false;
		}
	}

	async function fetchHistory() {
		const project = projectsStore.activeProject;
		if (!project) return;
		try {
			const res = await scansApi.list(project.id, {
				target_id: targetId,
				size: HISTORY_SIZE,
				sort_by: 'started',
				sort_dir: 'desc',
				include_focused: true
			});
			history = res.items;
			loaded('Runs');
		} catch {
			notLoadedNow('Runs');
		} finally {
			historyLoaded = true;
		}
	}

	async function fetchPrograms() {
		const project = projectsStore.activeProject;
		if (!project || !capabilitiesStore.has(Capability.BOUNTY_PROGRAMS)) return;
		try {
			programs = (await targetsApi.getPrograms(targetId, project.id)).items;
			loaded('Programs');
		} catch {
			notLoadedNow('Programs');
		}
	}

	async function settle<T>(section: string, work: Promise<T>, apply: (value: T) => void) {
		try {
			apply(await work);
			loaded(section);
		} catch {
			notLoadedNow(section);
		}
	}

	function certBucketsOf(buckets: { key: string; label: string; count: number }[]) {
		return buckets.map((b) => ({
			key: CERT_BUCKET_KEY[b.key] ?? b.key,
			label: b.label,
			count: b.count,
			query: CERT_FILTER[b.key] ?? EXPIRING_FILTER
		}));
	}

	let estateFor: string | null = null;
	async function fetchEstate(scanId: string | null) {
		const project = projectsStore.activeProject;
		const key = scanId ?? 'none';
		if (!project || estateFor === key) return;
		estateFor = key;
		await settle('Estate', targetsApi.getEstate(targetId, project.id, scanId), (e) => {
			estate = e;
		});
	}

	let webFor: string | null = null;
	async function fetchWebExtras(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || webFor === scanId) return;
		webFor = scanId;
		extrasLoading = true;
		const reachQueries = reachabilityStates(showDns).map((s) => s.query);
		await Promise.all([
			settle('Hosting', subdomainsApi.hosting(project.id, scanId), (h) => (hosting = h)),
			settle(
				'Technology',
				subdomainsApi.facets(project.id, scanId).then((f) => f.tech),
				(t) => (tech = t)
			),
			settle('Web hygiene', subdomainsApi.hygiene(project.id, scanId), (h) => (hygiene = h)),
			settle('Domain posture', domainPostureApi.target(project.id, targetId), (p) => (posture = p)),
			settle(
				'Domain posture',
				subdomainsApi.posture(project.id, scanId),
				(p) => (postureHosts = p)
			),
			settle(
				'Certificates',
				subdomainsApi.insights(project.id, scanId).then((i) => certBucketsOf(i.cert_buckets)),
				(b) => (certBuckets = b)
			),
			settle('Reachability', subdomainsApi.counts(project.id, scanId, reachQueries), (r) => {
				reach = r.counts;
			}),
			settle(
				'Exposures',
				interestApi.scan(scanId, { limit: EXPOSURE_ROWS }),
				(p) => (exposures = p)
			)
		]);
		if (webFor === scanId) extrasLoading = false;
	}

	let geoFor: string | null = null;
	async function fetchGeography(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || geoFor === scanId) return;
		geoFor = scanId;
		await settle('Geography', ipsApi.facets(project.id, scanId), (f) => (ipFacets = f));
	}

	let servicesFor: string | null = null;
	async function fetchServices(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || servicesFor === scanId) return;
		servicesFor = scanId;
		await settle('Services', servicesApi.exposure(project.id, scanId), (e) => (exposure = e));
	}

	let vulnsFor: string | null = null;
	async function fetchVulns(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || vulnsFor === scanId) return;
		vulnsFor = scanId;
		await settle('Findings', vulnerabilitiesApi.overview(project.id, scanId), (v) => (vulns = v));
	}

	let softwareFor: string | null = null;
	async function fetchSoftware(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || softwareFor === scanId) return;
		softwareFor = scanId;
		await settle(
			'Software CVEs',
			Promise.all([
				softwareApi.facets(project.id, scanId),
				softwareApi.coverage(project.id, scanId)
			]).then(([facets, coverage]) => ({ facets, coverage })),
			(s) => (software = s)
		);
	}

	function pickHosting(query: string) {
		if (!webScanId) return;
		goto(ROUTES.scanTab(webScanId, WEB.tab, { [WEB.queryParam]: query }));
	}

	function hasPendingEnrichment(): boolean {
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
			await Promise.all([fetchDetail(true), fetchTarget()]);
			if (!hasPendingEnrichment() || attempts >= MAX_ENRICHMENT_POLLS) {
				stopPolling();
				estateFor = null;
				fetchEstate(webScanId);
			}
		}, ENRICHMENT_POLL_MS);
	}

	function refreshAll(silent = true) {
		fetchSummary(silent);
		fetchHistory();
		if (!programsLoaded) {
			programsLoaded = true;
			fetchPrograms();
		}
	}

	$effect(() => {
		const id = targetId;
		if (id) {
			untrack(() => {
				fetchTarget();
				fetchDetail();
			});
		}
		activityScope.targetId = id;
		return () => activityScope.clear();
	});

	$effect(() => {
		if (target && untrack(hasPendingEnrichment) && !pollTimer) untrack(startPolling);
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = targetId;
		if (project && id) untrack(() => refreshAll(false));
	});

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => refreshAll());
	});

	$effect(() => {
		if (!live) return;
		const tick = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		const poll = setInterval(() => refreshAll(), 15_000);
		return () => {
			clearInterval(tick);
			clearInterval(poll);
		};
	});

	function refreshSections() {
		webFor = geoFor = servicesFor = vulnsFor = softwareFor = estateFor = null;
		void fetchSummary();
		void fetchHistory();
		void fetchPrograms();
		void fetchEstate(webScanId);
		if (webScanId) void fetchWebExtras(webScanId);
		if (ipsScanId) void fetchGeography(ipsScanId);
		if (servicesScanId) void fetchServices(servicesScanId);
		if (vulnScanId) void fetchVulns(vulnScanId);
		if (softwareScanId) void fetchSoftware(softwareScanId);
	}

	$effect(() => {
		const scanId = webScanId;
		if (scanId) untrack(() => fetchWebExtras(scanId));
	});
	$effect(() => {
		const scanId = webScanId;
		if (!summaryLoading) untrack(() => fetchEstate(scanId));
	});
	$effect(() => {
		const scanId = ipsScanId;
		if (scanId) untrack(() => fetchGeography(scanId));
	});
	$effect(() => {
		const scanId = servicesScanId;
		if (scanId) untrack(() => fetchServices(scanId));
	});
	$effect(() => {
		const scanId = vulnScanId;
		if (scanId) untrack(() => fetchVulns(scanId));
	});
	$effect(() => {
		const scanId = softwareScanId;
		if (scanId) untrack(() => fetchSoftware(scanId));
	});

	$effect(() => {
		const id = target?.created_by;
		creator = null;
		if (!id) return;
		usersApi
			.getSummary(id)
			.then((u) => {
				if (target?.created_by === id) creator = u.username;
			})
			.catch(() => {});
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

	onDestroy(() => {
		stopPolling();
		if (targetId) breadcrumbStore.remove(targetId);
	});

	function handleScan() {
		if (!target) return;
		showLaunchModal = true;
	}

	async function confirmCancel() {
		if (!latest) return;
		cancelling = true;
		const ok = await liveScans.cancel(latest);
		cancelling = false;
		cancelOpen = false;
		if (ok) {
			toast.success('Scan cancelled');
			refreshAll();
		} else toast.error('Scan not cancelled');
	}

	async function setSeedScans(on: boolean) {
		if (!target) return;
		const before = target.seed_scans;
		target = { ...target, seed_scans: on };
		try {
			await targetsApi.update(targetId, { seed_scans: on });
		} catch {
			target = target ? { ...target, seed_scans: before } : target;
			toast.error('Setting not saved.');
		}
	}

	async function setNewChecks(on: boolean) {
		if (!target) return;
		const before = target.new_checks;
		target = { ...target, new_checks: on };
		try {
			await targetsApi.update(targetId, { new_checks: on });
		} catch {
			target = target ? { ...target, new_checks: before } : target;
			toast.error('Setting not saved.');
		}
	}

	async function handleRefreshEnrichment() {
		if (!target) return;
		const requests: Promise<unknown>[] = [targetsApi.refreshWhois(target.id)];
		if (showDns) requests.push(targetsApi.refreshDns(target.id));
		if (showBgp) requests.push(targetsApi.refreshBgp(target.id));
		const results = await Promise.allSettled(requests);
		const failed = results.filter((r) => r.status === 'rejected').length;
		if (failed === results.length) toast.error('Enrichment refresh not started');
		else if (failed > 0) toast.error(`${failed} of ${results.length} lookups not started`);
		else toast.success('Enrichment refresh started');
		await fetchTarget();
		startPolling();
	}

	async function refreshOne(kind: 'dns' | 'whois' | 'bgp') {
		if (!target) return;
		const call = {
			dns: targetsApi.refreshDns,
			whois: targetsApi.refreshWhois,
			bgp: targetsApi.refreshBgp
		}[kind];
		refreshing = { ...refreshing, [kind]: true };
		try {
			await call(target.id);
			toast.success(`${kind.toUpperCase()} refresh started`);
			await fetchTarget();
			startPolling();
		} catch {
			toast.error(`${kind.toUpperCase()} refresh not started`);
		} finally {
			refreshing = { ...refreshing, [kind]: false };
		}
	}

	function patchTarget(patch: Partial<Target>) {
		if (target) target = { ...target, ...patch };
	}

	const fileName = (ext: string) =>
		`${(target?.target_value ?? 'target').replace(/[^a-z0-9.-]+/gi, '_')}.${ext}`;

	function handleExportJson() {
		if (!target) return;
		downloadBlob(
			fileName('json'),
			JSON.stringify({ target, detail, summary, scans: history, estate }, null, 2),
			'application/json'
		);
		toast.success('Target exported as JSON');
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
			...intel.rail.flatMap((g) =>
				g.rows.map(
					(r) =>
						[`${g.key}_${r.label.toLowerCase().replace(/\s+/g, '_')}`, r.value] as [string, string]
				)
			),
			['created_at', target.created_at],
			['updated_at', target.updated_at]
		];
		const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
		const csv = ['field,value', ...rows.map(([k, v]) => `${esc(k)},${esc(v)}`)].join('\n');
		downloadBlob(fileName('csv'), csv, 'text/csv');
		toast.success('Target exported as CSV');
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
			toast.error('Target not deleted');
		} finally {
			isDeleting = false;
		}
	}
</script>

<svelte:head><title>{target?.target_value ?? routeLabels.targets} · reNgine</title></svelte:head>

<svelte:window onkeydown={onKeydown} />

<div class="flex w-full flex-col gap-4 px-4 py-4 md:px-6">
	<a
		href={ROUTES.targets}
		class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="size-3.5" />
		Targets
	</a>

	{#if isLoading && !target}
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
		<div bind:this={headerEl}>
			<TargetHeader
				{target}
				{creator}
				{live}
				onScan={handleScan}
				onCancel={() => (cancelOpen = true)}
				onRefreshEnrichment={handleRefreshEnrichment}
				onExportJson={handleExportJson}
				onExportCsv={handleExportCsv}
				onDelete={() => (showDeleteDialog = true)}
				onReport={() => (reportOpen = true)}
				onChange={patchTarget}
			/>
		</div>

		{#if detailError && !detailLoading}
			<div
				class="flex items-center justify-between gap-3 rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3"
			>
				<p class="text-sm text-destructive">
					Enrichment not loaded. {detailError}
				</p>
				<Button variant="outline" size="sm" onclick={() => fetchDetail()}>Retry</Button>
			</div>
		{/if}

		{#if notLoaded.size}
			<div
				class="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-md border border-dashed px-4 py-2.5 text-sm text-muted-foreground"
			>
				<TriangleAlert class="size-4 shrink-0 text-warning" strokeWidth={1.5} />
				<span>{[...notLoaded].join(', ')} did not load.</span>
				<Button variant="outline" size="sm" class="ml-auto" onclick={refreshSections}>Retry</Button>
			</div>
		{/if}

		<Tabs.Root value={activeTab} onValueChange={setTab} style="--target-tabs-h: {tabsHeight}px">
			<div
				bind:clientHeight={tabsHeight}
				class="sticky top-0 z-30 -mx-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:-mx-6 md:px-6"
			>
				<div class="flex items-center gap-4">
					{#if condensed}
						<div
							class="hidden shrink-0 items-center gap-2 border-r border-border py-2 pr-4 sm:flex"
						>
							<span class="font-mono text-sm">{target.target_value}</span>
							{#if live}
								<Spinner class="size-3.5 text-info" />
							{/if}
						</div>
					{/if}
					<Tabs.List class="h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
						{#each tabs as key, i (key)}
							{@const t = TAB_DEFS[key]}
							{@const n = tabCounts[key]}
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Tabs.Trigger
											{...props}
											value={key}
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
			</div>

			<Tabs.Content value="overview" class="mt-4">
				<div class="flex flex-col gap-6">
					<SurfaceStrip
						targetId={target.id}
						{summary}
						loading={summaryLoading}
						{history}
						{run}
						onScan={handleScan}
					/>

					<!-- estate -->
					{#if estate && estate.counts.untracked > 0}
						<EstateTray
							count={estate.counts.untracked}
							subject={target.target_value}
							domains={estate.domains}
							providers={estate.providers}
							neighbours={estate.neighbours}
							sheetDescription="{estate.domains.length} domains · {estate.providers
								.length} providers · {estate.considered_targets} targets considered"
						/>
					{/if}

					{#if showReach && reach && webScanId}
						<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
							<ReachabilityCell
								counts={reach}
								isDomain={showDns}
								scanId={webScanId}
								observedAt={webObservedAt}
								loading={extrasLoading}
								class="col-span-12"
							/>
						</div>
					{/if}

					{#if showFindings || showPosture}
						<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
							{#if showFindings && summary && vulnScanId}
								<FindingsCell
									risk={summary.risk}
									{vulns}
									scanId={vulnScanId}
									loading={extrasLoading}
									class="col-span-12 {showPosture ? 'lg:col-span-6 xl:col-span-8' : ''}"
								/>
							{/if}
							{#if showPosture}
								<PostureCell
									targetId={target.id}
									checks={intel.checks}
									sensitive={summary?.sensitive_services ?? 0}
									{servicesScanId}
									loading={detailLoading}
									class="col-span-12 {showFindings ? 'lg:col-span-6 xl:col-span-4' : ''}"
								/>
							{/if}
						</div>
					{/if}

					<!-- composition -->
					{#if compositionKeys.length}
						<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
							{#each compositionKeys as key, i (key)}
								{@const cls = compositionSpans[i]}
								{#if key === 'geo'}
									<GeoCell countries={ipFacets?.country ?? null} scanId={ipsScanId} class={cls} />
								{:else if key === 'hosting' && hosting && webScanId}
									<HostingCell {hosting} scanId={webScanId} onPick={pickHosting} class={cls} />
								{:else if key === 'services' && servicesExposure}
									<ServicesCell exposure={servicesExposure} scanId={servicesScanId} class={cls} />
								{:else if key === 'tech'}
									<TechCell {tech} scanId={webScanId} class={cls} />
								{:else if key === 'hygiene'}
									<HygieneCell {hygiene} scanId={webScanId} class={cls} />
								{:else if key === 'domain-posture'}
									<DomainPostureCell
										summary={posture}
										hosts={postureHosts}
										scanId={posture?.scan_id}
										class={cls}
									/>
								{:else if key === 'software'}
									<SoftwareCell {software} scanId={softwareScanId} class={cls} />
								{:else if key === 'certs' && certBuckets}
									<CertsCell
										buckets={certBuckets}
										expiringQuery={EXPIRING_FILTER}
										scanId={webScanId}
										class={cls}
									/>
								{:else if key === 'exposures'}
									<ExposuresCell page={exposures} scanId={webScanId} class={cls} />
								{/if}
							{/each}
						</div>
					{/if}

					<!-- identity -->
					<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
						{#each identityKeys as key, i (key)}
							{@const cls = identitySpans[i]}
							{@const group = intel.rail.find((g) => g.key === key)}
							{#if group}
								<IdentityCell targetId={target.id} {group} loading={detailLoading} class={cls} />
							{:else if key === 'programs'}
								<ProgramsCell {programs} class={cls} />
							{:else if key === 'monitoring' && summary}
								<MonitoringCell
									{summary}
									{enrichedAt}
									seedScans={target.seed_scans}
									onToggleSeeds={setSeedScans}
									newChecks={target.new_checks}
									onToggleNewChecks={setNewChecks}
									onRefresh={handleRefreshEnrichment}
									class={cls}
								/>
							{:else if key === 'seeds'}
								<SeedsCell targetId={target.id} class={cls} />
							{/if}
						{/each}
					</div>

					<!-- activity -->
					<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
						<ActivityCell
							{target}
							{creator}
							{summary}
							{history}
							loaded={historyLoaded}
							{run}
							{now}
							class="col-span-12 {showRuns ? 'xl:col-span-7' : ''}"
						/>
						{#if showRuns}
							<RunsCell {history} class="col-span-12 xl:col-span-5" />
						{/if}
					</div>
				</div>
			</Tabs.Content>

			<Tabs.Content value="web-assets" class="mt-4">
				<TargetWebAssets targetId={target.id} onScan={handleScan} />
			</Tabs.Content>

			{#if showDns}
				<Tabs.Content value="dns" class="mt-4">
					<DnsTab
						host={detail?.dns?.host ?? target.target_value}
						lookup={detail?.dns ?? null}
						status={dnsStatus}
						error={detail?.dns_error ?? target.dns_error}
						loading={detailLoading}
						refreshing={!!refreshing.dns}
						{ipsScanId}
						onRefresh={() => refreshOne('dns')}
					/>
				</Tabs.Content>
			{/if}

			<Tabs.Content value="whois" class="mt-4">
				<WhoisTab
					targetValue={target.target_value}
					targetType={target.target_type}
					record={detail?.whois ?? null}
					status={whoisStatus}
					error={detail?.whois_error ?? target.whois_error}
					loading={detailLoading}
					refreshing={!!refreshing.whois}
					onRefresh={() => refreshOne('whois')}
				/>
			</Tabs.Content>

			{#if showBgp}
				<Tabs.Content value="bgp" class="mt-4">
					<BgpTab
						targetValue={target.target_value}
						targetType={target.target_type}
						bgp={detail?.bgp ?? null}
						status={bgpStatus}
						loading={detailLoading}
						refreshing={!!refreshing.bgp}
						onRefresh={() => refreshOne('bgp')}
					/>
				</Tabs.Content>
			{/if}

			<Tabs.Content value="notes" class="mt-4">
				<div class="overflow-hidden rounded-xl border bg-card">
					<NotePanel
						anchor={{ targetId: target.id }}
						filter={{ target_id: target.id }}
						emptyTitle="No notes on this target"
						emptyDescription="Add a note from one of its assets."
						onCount={(n) => (notesTotal = n)}
					/>
				</div>
			</Tabs.Content>
		</Tabs.Root>
	{/if}
</div>

{#if target}
	<GenerateReportDialog
		bind:open={reportOpen}
		projectId={target.project_id}
		targetId={target.id}
		subject={target.target_value}
	/>
	<LaunchDialog
		bind:open={showLaunchModal}
		targetId={target.id}
		onClose={() => {
			showLaunchModal = false;
			refreshAll();
			scansStore.refresh();
		}}
	/>

	<ConfirmDialog
		bind:open={cancelOpen}
		title="Cancel scan"
		description="The scan is marked cancelled. Finished stages keep their results."
		confirmLabel="Cancel scan"
		loading={cancelling}
		onOpenChange={(open) => (cancelOpen = open)}
		onConfirm={confirmCancel}
	/>

	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete target"
		description="Target {target.target_value} and its scans and findings are removed."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={confirmDelete}
	/>
{/if}
