import { dashboardApi } from '$lib/api/dashboard';
import { subdomainsApi } from '$lib/api/subdomains';
import { domainPostureApi } from '$lib/api/domain-posture';
import { interestApi } from '$lib/api/interest';
import { ipsApi, softwareApi } from '$lib/api/scan-results';
import { threatIntelApi } from '$lib/api/threat-intel';
import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
import { Capability } from '$lib/config/capabilities';
import type { Facet } from '$lib/utilities/scan-insights';
import type { IpFacetSet } from '$lib/utilities/ip-groups';
import type { InterestPage } from '$lib/types/interest';
import type { IntelChange, ThreatIntelStatus } from '$lib/types/threat-intel';
import type { SoftwareCoverage, SoftwareFacets } from '$lib/types/software';
import type { HygieneSummary } from '$lib/utilities/scan-insights';
import type { DomainPostureSummary } from '$lib/types/domain-posture';
import type { CorrelationGraph } from '$lib/types/correlation';
import { SvelteSet } from 'svelte/reactivity';
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
	type DashboardWindow,
	type HostingSplit
} from '$lib/types/dashboard';

const EXPOSURE_ROWS = 6;
const CHANGE_ROWS = 200;

function hostingCounts(projectId: string): Promise<HostingSplit> {
	const queries = Object.values(HOSTING_QUERIES);
	return subdomainsApi.counts(projectId, '', queries).then((r) => ({
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
	let posture = $state<DomainPostureSummary | null>(null);
	let postureHosts = $state<HygieneSummary | null>(null);
	let shared = $state<CorrelationGraph | null>(null);
	let activity = $state<DashboardActivity | null>(null);
	let programs = $state<DashboardPrograms | null>(null);
	let extrasLoading = $state(false);
	let changeWindow = $state<DashboardWindow>(DEFAULT_DASHBOARD_WINDOW);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);
	const failed = new SvelteSet<DashboardSlice>();
	let seq = 0;

	async function load() {
		const pid = projectId;
		const win = changeWindow;
		if (!pid) return;
		const mySeq = ++seq;
		loading = true;
		void loadDiscovery(pid, mySeq);
		void loadExtras(pid, win, mySeq);
		try {
			const data = await dashboardApi.overview(pid, win);
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

	// worker ping only on first run
	async function loadReadiness(mySeq: number) {
		try {
			const data = await dashboardApi.readiness();
			if (mySeq === seq) readiness = data;
		} catch {
			if (mySeq === seq) readiness = null;
		}
	}

	// slow rollup, loaded after first paint
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

	// each cell reads its result page's own endpoint
	async function loadExtras(pid: string, win: DashboardWindow, mySeq: number) {
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
			settle(
				'tech',
				subdomainsApi.facets(pid, '').then((f) => f.tech),
				(v) => (tech = v)
			),
			settle('ipFacets', ipsApi.facets(pid, ''), (v) => (ipFacets = v)),
			settle('intel', threatIntelApi.status(pid), (v) => (intel = v)),
			settle(
				'changes',
				threatIntelApi.changes(pid, windowDays(win), CHANGE_ROWS),
				(v) => (changes = v)
			),
			settle('hosting', hostingCounts(pid), (v) => (hosting = v)),
			settle(
				'exposures',
				interestApi.project(pid, { limit: EXPOSURE_ROWS }),
				(v) => (exposures = v)
			),
			settle(
				'software',
				Promise.all([softwareApi.facets(pid, ''), softwareApi.coverage(pid, '')]).then(
					([facets, coverage]) => ({ facets, coverage })
				),
				(v) => (software = v)
			),
			settle('hygiene', subdomainsApi.hygiene(pid, ''), (v) => (hygiene = v)),
			settle('posture', domainPostureApi.project(pid), (v) => (posture = v)),
			settle('posture', subdomainsApi.posture(pid, ''), (v) => (postureHosts = v)),
			settle('shared', subdomainsApi.correlationGraph(pid, ''), (v) => (shared = v)),
			settle('activity', dashboardApi.activity(pid, win), (v) => (activity = v)),
			bounty
				? settle('programs', dashboardApi.programs(pid, win), (v) => (programs = v))
				: Promise.resolve()
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
		posture = null;
		postureHosts = null;
		shared = null;
		activity = null;
		programs = null;
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
		get extrasLoading() {
			return extrasLoading;
		},
		get window() {
			return changeWindow;
		},
		get loading() {
			return loading;
		},
		get error() {
			return error;
		},
		get hasFetched() {
			return hasFetched;
		},
		get failedSlices(): DashboardSlice[] {
			return DASHBOARD_SLICES.filter((slice) => failed.has(slice));
		},

		init(pid: string) {
			if (pid === projectId) {
				if (!hasFetched && !loading) void load();
				return;
			}
			projectId = pid;
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
			loading = false;
		}
	};
}

export const dashboardStore = createDashboardStore();
