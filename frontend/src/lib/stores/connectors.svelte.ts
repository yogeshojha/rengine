import { connectorsApi } from '$lib/api/connectors';
import type {
	CandidatePage,
	CandidateQuery,
	Connector,
	ConnectorSpec,
	DiscoveredDomain
} from '$lib/types/connector';

function createConnectorsStore() {
	let catalog = $state<ConnectorSpec[]>([]);
	let catalogPending: Promise<void> | null = null;
	let items = $state<Connector[]>([]);
	let queue = $state<CandidatePage | null>(null);
	let discovered = $state<DiscoveredDomain[]>([]);
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
		get discovered() {
			return discovered;
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
			discovered = [];
		},

		async loadCatalog() {
			if (catalog.length) return;
			catalogPending ??= connectorsApi
				.catalog()
				.then((c) => {
					catalog = c;
				})
				.catch((e) => {
					error = message(e, 'Connector catalog not loaded');
				})
				.finally(() => {
					catalogPending = null;
				});
			return catalogPending;
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
				error = message(e, 'Connectors not loaded');
			} finally {
				isLoading = false;
			}
		},

		async loadQueue(id: string, projectId: string, params: CandidateQuery = {}) {
			queueLoading = true;
			try {
				queue = await connectorsApi.candidates(id, projectId, params);
			} catch (e) {
				error = message(e, 'Queue not loaded');
			} finally {
				queueLoading = false;
			}
		},

		async loadDiscovered(id: string, projectId: string) {
			try {
				discovered = await connectorsApi.discovered(id, projectId);
			} catch (e) {
				error = message(e, 'Discovered domains not loaded');
			}
		},

		upsert(connector: Connector, select = false) {
			const at = items.findIndex((c) => c.id === connector.id);
			if (at >= 0) items[at] = connector;
			else items = [connector, ...items];
			if (select) selectedId = connector.id;
		},

		drop(id: string) {
			items = items.filter((c) => c.id !== id);
			if (selectedId === id) selectedId = items[0]?.id ?? null;
		},

		reset() {
			catalog = [];
			items = [];
			queue = null;
			discovered = [];
			isLoading = false;
			queueLoading = false;
			error = null;
			fetchedProjectId = null;
			selectedId = null;
		}
	};
}

export const connectors = createConnectorsStore();
