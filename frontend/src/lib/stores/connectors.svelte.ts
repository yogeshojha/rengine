import { connectorsApi } from '$lib/api/connectors';
import type {
	CandidatePage,
	Connector,
	ConnectorCoverage,
	ConnectorSession,
	ConnectorSpec,
	DiscoveredDomain
} from '$lib/types/connector';

function createConnectorsStore() {
	let catalog = $state<ConnectorSpec[]>([]);
	let items = $state<Connector[]>([]);
	let queue = $state<CandidatePage | null>(null);
	let coverage = $state<ConnectorCoverage[]>([]);
	let discovered = $state<DiscoveredDomain[]>([]);
	let sessions = $state<ConnectorSession[]>([]);
	let isLoading = $state(false);
	let queueLoading = $state(false);
	let error = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let selectedId = $state<string | null>(null);

	function message(e: unknown, fallback: string) {
		return e instanceof Error ? e.message : fallback;
	}

	return {
		get catalog() {
			return catalog;
		},
		get items() {
			return items;
		},
		get queue() {
			return queue;
		},
		get coverage() {
			return coverage;
		},
		get discovered() {
			return discovered;
		},
		get sessions() {
			return sessions;
		},
		get isLoading() {
			return isLoading;
		},
		get queueLoading() {
			return queueLoading;
		},
		get error() {
			return error;
		},
		get fetchedProjectId() {
			return fetchedProjectId;
		},
		get selectedId() {
			return selectedId;
		},
		get selected() {
			return items.find((c) => c.id === selectedId) ?? items[0] ?? null;
		},

		select(id: string | null) {
			selectedId = id;
			queue = null;
			coverage = [];
			discovered = [];
			sessions = [];
		},

		async loadCatalog() {
			if (catalog.length) return;
			try {
				catalog = await connectorsApi.catalog();
			} catch (e) {
				error = message(e, 'Connector catalog could not be loaded');
			}
		},

		async load(projectId: string, force = false) {
			if (isLoading) return;
			if (!force && fetchedProjectId === projectId) return;
			isLoading = true;
			error = null;
			try {
				items = await connectorsApi.list(projectId);
				fetchedProjectId = projectId;
				if (!items.some((c) => c.id === selectedId)) selectedId = items[0]?.id ?? null;
			} catch (e) {
				error = message(e, 'Connectors could not be loaded');
			} finally {
				isLoading = false;
			}
		},

		async loadQueue(
			id: string,
			projectId: string,
			params: {
				state?: string;
				host?: string;
				notice?: string;
				search?: string;
				page?: number;
			} = {}
		) {
			queueLoading = true;
			try {
				queue = await connectorsApi.candidates(id, projectId, params);
			} catch (e) {
				error = message(e, 'The queue could not be loaded');
			} finally {
				queueLoading = false;
			}
		},

		async loadDiscovered(id: string, projectId: string) {
			try {
				discovered = await connectorsApi.discovered(id, projectId);
			} catch (e) {
				error = message(e, 'Discovered domains could not be loaded');
			}
		},

		async loadCoverage(id: string, projectId: string) {
			try {
				coverage = await connectorsApi.coverage(id, projectId);
			} catch (e) {
				error = message(e, 'Coverage could not be loaded');
			}
		},

		async loadSessions(id: string, projectId: string) {
			try {
				sessions = await connectorsApi.sessions(id, projectId);
			} catch (e) {
				error = message(e, 'Sessions could not be loaded');
			}
		},

		upsert(connector: Connector) {
			const at = items.findIndex((c) => c.id === connector.id);
			if (at >= 0) items[at] = connector;
			else items = [connector, ...items];
			selectedId = connector.id;
		},

		drop(id: string) {
			items = items.filter((c) => c.id !== id);
			if (selectedId === id) selectedId = items[0]?.id ?? null;
		},

		reset() {
			catalog = [];
			items = [];
			queue = null;
			coverage = [];
			discovered = [];
			sessions = [];
			isLoading = false;
			queueLoading = false;
			error = null;
			fetchedProjectId = null;
			selectedId = null;
		}
	};
}

export const connectors = createConnectorsStore();
