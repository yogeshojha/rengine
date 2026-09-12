import { dashboardApi } from '$lib/api/dashboard';
import { subdomainsApi } from '$lib/api/subdomains';
import { interestApi } from '$lib/api/interest';
import { endpointsApi, ipsApi, servicesApi } from '$lib/api/scan-results';
import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
import { threatIntelApi } from '$lib/api/threat-intel';
import { compileVulnQuery, emptyVulnQuery } from '$lib/utilities/vulns';
import { compileServiceQuery, emptyServiceQuery } from '$lib/utilities/services';
import type { Facet } from '$lib/utilities/scan-insights';
import type { IpFacetSet } from '$lib/utilities/ip-groups';
import type { InterestPage } from '$lib/types/interest';
import type { ThreatIntelStatus } from '$lib/types/threat-intel';
import {
	DEFAULT_DASHBOARD_WINDOW,
	FEED_QUERIES,
	HOSTING_QUERIES,
	type DashboardDiscovery,
	type DashboardFeed,
	type DashboardOverview,
	type DashboardReadiness,
	type DashboardWindow,
	type HostingSplit
} from '$lib/types/dashboard';

const FEED_ROWS = 4;
const EXPOSURE_ROWS = 8;

function hostingCounts(projectId: string): Promise<HostingSplit> {
	const queries = Object.values(HOSTING_QUERIES);
	return subdomainsApi.counts(projectId, '', queries).then((r) => ({
		resolved: r.counts[HOSTING_QUERIES.resolved] ?? 0,
		edge: r.counts[HOSTING_QUERIES.edge] ?? 0,
		cloud: r.counts[HOSTING_QUERIES.cloud] ?? 0,
		direct: r.counts[HOSTING_QUERIES.direct] ?? 0
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
	let hosting = $state<HostingSplit | null>(null);
	let exposures = $state<InterestPage | null>(null);
	let feed = $state<DashboardFeed | null>(null);
	let extrasLoading = $state(false);
	let changeWindow = $state<DashboardWindow>(DEFAULT_DASHBOARD_WINDOW);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);
	let seq = 0;

	async function load() {
		const pid = projectId;
		const win = changeWindow;
		if (!pid) return;
		const mySeq = ++seq;
		loading = true;
		try {
			const data = await dashboardApi.overview(pid, win);
			if (mySeq !== seq) return;
			overview = data;
			error = null;
			hasFetched = true;
		} catch (e) {
			if (mySeq !== seq) return;
			error = e instanceof Error ? e.message : 'Dashboard could not be loaded';
		} finally {
			if (mySeq === seq) loading = false;
		}
		void loadDiscovery(pid, mySeq);
		void loadExtras(pid, mySeq);
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
			if (mySeq === seq) discovery = data;
		} catch {
			if (mySeq === seq) discovery = null;
		}
	}

	// each widget reads its result page's own endpoint
	async function loadExtras(pid: string, mySeq: number) {
		extrasLoading = true;
		const keep = () => mySeq === seq;
		const settle = async <T>(work: Promise<T>, apply: (value: T | null) => void) => {
			try {
				const value = await work;
				if (keep()) apply(value);
			} catch {
				if (keep()) apply(null);
			}
		};
		await Promise.all([
			settle(
				subdomainsApi.facets(pid, '').then((f) => f.tech),
				(v) => (tech = v)
			),
			settle(ipsApi.facets(pid, ''), (v) => (ipFacets = v)),
			settle(threatIntelApi.status(pid), (v) => (intel = v)),
			settle(hostingCounts(pid), (v) => (hosting = v)),
			settle(interestApi.project(pid, { limit: EXPOSURE_ROWS }), (v) => (exposures = v)),
			settle(
				Promise.all([
					vulnerabilitiesApi.search(
						pid,
						'',
						compileVulnQuery({ ...emptyVulnQuery(), newOnly: true }, 'risk', -1, 0, FEED_ROWS)
					),
					interestApi.project(pid, { q: FEED_QUERIES.exposures, limit: FEED_ROWS }),
					servicesApi.search(
						pid,
						'',
						compileServiceQuery(
							{ ...emptyServiceQuery(), newOnly: true, sensitiveOnly: true },
							'exposure',
							-1,
							0,
							FEED_ROWS
						)
					),
					endpointsApi.search(pid, '', {
						q: FEED_QUERIES.endpoints,
						host: null,
						dir_path: null,
						subtree: true,
						endpoint_class: null,
						source: null,
						interest: null,
						status_class: null,
						probed: null,
						new: false,
						hide_static: true,
						sort: 'relevance',
						direction: 'desc',
						page: 1,
						size: FEED_ROWS
					})
				]).then(([vulns, fresh, services, endpoints]) => ({
					vulns: { items: vulns.items, total: vulns.total },
					exposures: { rows: fresh.rows, total: fresh.total },
					services: { items: services.items, total: services.total },
					endpoints: { items: endpoints.items, total: endpoints.total }
				})),
				(v) => (feed = v)
			)
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
		hosting = null;
		exposures = null;
		feed = null;
		extrasLoading = false;
		error = null;
		hasFetched = false;
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
		get hosting() {
			return hosting;
		},
		get exposures() {
			return exposures;
		},
		get feed() {
			return feed;
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
