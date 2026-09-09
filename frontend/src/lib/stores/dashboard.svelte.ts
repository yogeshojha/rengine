import { dashboardApi } from '$lib/api/dashboard';
import { subdomainsApi } from '$lib/api/subdomains';
import { interestApi } from '$lib/api/interest';
import { endpointsApi, ipsApi, servicesApi } from '$lib/api/scan-results';
import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
import { compileVulnQuery, emptyVulnQuery } from '$lib/utilities/vulns';
import { compileServiceQuery, emptyServiceQuery } from '$lib/utilities/services';
import type { Facet, SubdomainFilter } from '$lib/utilities/scan-insights';
import type { IpFacetSet } from '$lib/utilities/ip-groups';
import type { InterestPage } from '$lib/types/interest';
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

function hostCount(projectId: string, q: string) {
	const filter: SubdomainFilter = {
		q,
		statuses: [],
		tech: [],
		services: [],
		cert: [],
		sources: [],
		cdn: 'any',
		waf: 'any',
		live: false,
		screenshot: false,
		issues: false,
		new: false,
		sort: 'status',
		order: 'asc',
		limit: 1,
		offset: 0
	};
	return subdomainsApi.search(projectId, '', filter).then((r) => r.total);
}

function createDashboardStore() {
	let projectId = $state<string | undefined>(undefined);
	let overview = $state<DashboardOverview | null>(null);
	let discovery = $state<DashboardDiscovery | null>(null);
	let readiness = $state<DashboardReadiness | null>(null);
	let tech = $state<Facet[] | null>(null);
	let ipFacets = $state<IpFacetSet | null>(null);
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

	// a worker ping is a broker round trip, so only a first run asks for it
	async function loadReadiness(mySeq: number) {
		try {
			const data = await dashboardApi.readiness();
			if (mySeq === seq) readiness = data;
		} catch {
			if (mySeq === seq) readiness = null;
		}
	}

	// the certificate walk is the one slow rollup, so it lands after the page has painted
	async function loadDiscovery(pid: string, mySeq: number) {
		try {
			const data = await dashboardApi.discovery(pid);
			if (mySeq === seq) discovery = data;
		} catch {
			if (mySeq === seq) discovery = null;
		}
	}

	// every widget that reads a project-wide result page asks that page's own endpoint, so its count is that page's count
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
			settle(
				Promise.all([
					hostCount(pid, HOSTING_QUERIES.resolved),
					hostCount(pid, HOSTING_QUERIES.edge),
					hostCount(pid, HOSTING_QUERIES.cloud),
					hostCount(pid, HOSTING_QUERIES.direct)
				]).then(([resolved, edge, cloud, direct]) => ({ resolved, edge, cloud, direct })),
				(v) => (hosting = v)
			),
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
			void load();
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
