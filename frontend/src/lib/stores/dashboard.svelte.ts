import { dashboardApi } from '$lib/api/dashboard';
import { subdomainsApi } from '$lib/api/subdomains';
import { domainPostureApi } from '$lib/api/domain-posture';
import { interestApi } from '$lib/api/interest';
import { ipsApi, servicesApi, softwareApi } from '$lib/api/scan-results';
import { threatIntelApi } from '$lib/api/threat-intel';
import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
import { Capability } from '$lib/config/capabilities';
import { INTEL_CHANGE_ROWS } from '$lib/config/dashboard';
import type { Facet } from '$lib/utilities/scan-insights';
import type { IpFacetSet } from '$lib/utilities/ip-groups';
import type { InterestPage } from '$lib/types/interest';
import type { IntelChange, ThreatIntelStatus } from '$lib/types/threat-intel';
import type { SoftwareCoverage, SoftwareFacets } from '$lib/types/software';
import type { AiSummary, HygieneSummary } from '$lib/utilities/scan-insights';
import type { DomainPostureSummary } from '$lib/types/domain-posture';
import type { CorrelationGraph } from '$lib/types/correlation';
import { SvelteSet } from 'svelte/reactivity';
import { sameTargetScope, type TargetScope } from '$lib/utilities/surface-scope';
import {
	DASHBOARD_SLICES,
	DEFAULT_DASHBOARD_WINDOW,
	HOSTING_QUERIES,
	windowDays,
	type DashboardActivity,
	type DashboardSlice,
	type DashboardDiscovery,
	type DashboardOverview,
	type DashboardPrograms,
	type DashboardReadiness,
	type DashboardSurfaceRisk,
	type DashboardWindow,
	type DashboardWindowCounts,
	type HostingSplit
} from '$lib/types/dashboard';

const EXPOSURE_ROWS = 6;

function hostingCounts(projectId: string, scope: TargetScope): Promise<HostingSplit> {
	const queries = Object.values(HOSTING_QUERIES);
	return subdomainsApi.counts(projectId, '', queries, scope).then((r) => ({
		resolved: r.counts[HOSTING_QUERIES.resolved] ?? 0,
		edge: r.counts[HOSTING_QUERIES.edge] ?? 0,
		cloud: r.counts[HOSTING_QUERIES.cloud] ?? 0,
		direct: r.counts[HOSTING_QUERIES.direct] ?? 0,
		capped: r.capped ?? {}
	}));
}

function createDashboardStore() {
	let projectId = $state<string | undefined>(undefined);
	let overview = $state<DashboardOverview | null>(null);
	let discovery = $state<DashboardDiscovery | null>(null);
	let readiness = $state<DashboardReadiness | null>(null);
	let tech = $state<Facet[] | null>(null);
	let ipFacets = $state<IpFacetSet | null>(null);
	let intel = $state<ThreatIntelStatus | null>(null);
	let changes = $state<IntelChange[] | null>(null);
	let hosting = $state<HostingSplit | null>(null);
	let exposures = $state<InterestPage | null>(null);
	let software = $state<{ facets: SoftwareFacets; coverage: SoftwareCoverage } | null>(null);
	let hygiene = $state<HygieneSummary | null>(null);
	let ai = $state<AiSummary | null>(null);
	let posture = $state<DomainPostureSummary | null>(null);
	let postureHosts = $state<HygieneSummary | null>(null);
	let shared = $state<CorrelationGraph | null>(null);
	let activity = $state<DashboardActivity | null>(null);
	let programs = $state<DashboardPrograms | null>(null);
	let surfaceRisk = $state<DashboardSurfaceRisk | null>(null);
	let windowCounts = $state<DashboardWindowCounts | null>(null);
	let windowLoading = $state(false);
	let extrasLoading = $state(false);
	let changeWindow = $state<DashboardWindow>(DEFAULT_DASHBOARD_WINDOW);
	let scope = $state<TargetScope>({});
	let loading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);
	const failed = new SvelteSet<DashboardSlice>();
	let seq = 0;

	async function load() {
		const pid = projectId;
		const win = changeWindow;
		const sc = $state.snapshot(scope);
		if (!pid) return;
		const mySeq = ++seq;
		loading = true;
		const pending = dashboardApi.overview(pid, win, sc);
		void loadWindow(pid, win, sc, mySeq);
		void loadExtras(pid, win, sc, mySeq);
		void loadDiscovery(pid, mySeq);
		try {
			const data = await pending;
			if (mySeq !== seq) return;
			overview = data;
			error = null;
			hasFetched = true;
		} catch (e) {
			if (mySeq !== seq) return;
			error = e instanceof Error ? e.message : 'Dashboard not loaded';
		} finally {
			if (mySeq === seq) loading = false;
		}
		if (overview?.first_run) void loadReadiness(mySeq);
	}

	async function loadReadiness(mySeq: number) {
		try {
			const data = await dashboardApi.readiness();
			if (mySeq === seq) readiness = data;
		} catch {
			if (mySeq === seq) readiness = null;
		}
	}

	async function loadWindow(pid: string, win: DashboardWindow, sc: TargetScope, mySeq: number) {
		windowLoading = true;
		try {
			const data = await dashboardApi.window(pid, win, sc);
			if (mySeq !== seq) return;
			windowCounts = data;
			failed.delete('window');
		} catch {
			if (mySeq !== seq) return;
			windowCounts = null;
			failed.add('window');
		} finally {
			if (mySeq === seq) windowLoading = false;
		}
	}

	async function loadDiscovery(pid: string, mySeq: number) {
		try {
			const data = await dashboardApi.discovery(pid);
			if (mySeq !== seq) return;
			discovery = data;
			failed.delete('discovery');
		} catch {
			if (mySeq !== seq) return;
			discovery = null;
			failed.add('discovery');
		}
	}

	async function loadExtras(pid: string, win: DashboardWindow, sc: TargetScope, mySeq: number) {
		extrasLoading = true;
		const keep = () => mySeq === seq;
		const settle = async <T>(
			slice: DashboardSlice,
			work: Promise<T>,
			apply: (value: T | null) => void
		) => {
			try {
				const value = await work;
				if (!keep()) return;
				apply(value);
				failed.delete(slice);
			} catch {
				if (!keep()) return;
				apply(null);
				failed.add(slice);
			}
		};
		const bounty = capabilitiesStore.has(Capability.BOUNTY_PROGRAMS);
		await Promise.all([
			settle('surfaceRisk', dashboardApi.surfaceRisk(pid, sc), (v) => (surfaceRisk = v)),
			bounty
				? settle('programs', dashboardApi.programs(pid, win), (v) => (programs = v))
				: Promise.resolve(),
			settle(
				'tech',
				subdomainsApi.facets(pid, '', sc).then((f) => f.tech),
				(v) => (tech = v)
			),
			settle('ipFacets', ipsApi.facets(pid, '', sc), (v) => (ipFacets = v)),
			settle('intel', threatIntelApi.status(pid, sc), (v) => (intel = v)),
			settle(
				'changes',
				threatIntelApi.changes(pid, windowDays(win), INTEL_CHANGE_ROWS, sc),
				(v) => (changes = v)
			),
			settle('hosting', hostingCounts(pid, sc), (v) => (hosting = v)),
			settle(
				'exposures',
				interestApi.project(pid, { limit: EXPOSURE_ROWS }, sc),
				(v) => (exposures = v)
			),
			settle(
				'software',
				Promise.all([softwareApi.facets(pid, '', sc), softwareApi.coverage(pid, '', sc)]).then(
					([facets, coverage]) => ({ facets, coverage })
				),
				(v) => (software = v)
			),
			settle('hygiene', subdomainsApi.hygiene(pid, '', sc), (v) => (hygiene = v)),
			settle('ai', servicesApi.ai(pid, '', sc), (v) => (ai = v)),
			settle(
				'posture',
				Promise.all([domainPostureApi.project(pid, sc), subdomainsApi.posture(pid, '', sc)]).then(
					([zones, hosts]) => ({ zones, hosts })
				),
				(v) => {
					posture = v?.zones ?? null;
					postureHosts = v?.hosts ?? null;
				}
			),
			settle('activity', dashboardApi.activity(pid, win, sc), (v) => (activity = v)),
			settle('shared', subdomainsApi.correlationGraph(pid, '', sc), (v) => (shared = v))
		]);
		if (keep()) extrasLoading = false;
	}

	function resetData() {
		overview = null;
		discovery = null;
		readiness = null;
		tech = null;
		ipFacets = null;
		intel = null;
		changes = null;
		hosting = null;
		exposures = null;
		software = null;
		hygiene = null;
		ai = null;
		posture = null;
		postureHosts = null;
		shared = null;
		activity = null;
		programs = null;
		surfaceRisk = null;
		windowCounts = null;
		windowLoading = false;
		extrasLoading = false;
		error = null;
		hasFetched = false;
		failed.clear();
	}

	return {
		get overview() {
			return overview;
		},
		get discovery() {
			return discovery;
		},
		get readiness() {
			return readiness;
		},
		get tech() {
			return tech;
		},
		get ipFacets() {
			return ipFacets;
		},
		get intel() {
			return intel;
		},
		get changes() {
			return changes;
		},
		get hosting() {
			return hosting;
		},
		get exposures() {
			return exposures;
		},
		get software() {
			return software;
		},
		get hygiene() {
			return hygiene;
		},
		get ai() {
			return ai;
		},
		get posture() {
			return posture;
		},
		get postureHosts() {
			return postureHosts;
		},
		get shared() {
			return shared;
		},
		get activity() {
			return activity;
		},
		get programs() {
			return programs;
		},
		get surfaceRisk() {
			return surfaceRisk;
		},
		get windowCounts() {
			return windowCounts;
		},
		get windowLoading() {
			return windowLoading;
		},
		get extrasLoading() {
			return extrasLoading;
		},
		get window() {
			return changeWindow;
		},
		get scope(): TargetScope {
			return scope;
		},
		get loading() {
			return loading;
		},
		get error() {
			return error;
		},
		get failedSlices(): DashboardSlice[] {
			return DASHBOARD_SLICES.filter((slice) => failed.has(slice));
		},

		init(pid: string, next: TargetScope = {}) {
			if (pid === projectId) {
				if (!sameTargetScope(scope, next)) {
					scope = next;
					void load();
				} else if (!hasFetched && !loading) void load();
				return;
			}
			projectId = pid;
			scope = next;
			resetData();
			void load();
		},

		refresh() {
			if (!loading) void load();
		},

		markStale() {
			hasFetched = false;
		},

		setWindow(win: DashboardWindow) {
			if (win === changeWindow) return;
			changeWindow = win;
			void load();
		},

		clear() {
			seq++;
			projectId = undefined;
			resetData();
			changeWindow = DEFAULT_DASHBOARD_WINDOW;
			scope = {};
			loading = false;
		}
	};
}

export const dashboardStore = createDashboardStore();
