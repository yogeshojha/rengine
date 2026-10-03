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
	let queueError = $state<string | null>(null);
	let discoveredError = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let loadedAt = 0;
	let queueSeq = 0;

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
		get queueLoading() {
			return queueLoading;
		},
		get error() {
			return error;
		},
		get queueError() {
			return queueError;
		},
		get discoveredError() {
			return discoveredError;
		},
		get fetchedProjectId() {
			return fetchedProjectId;
		},
		get loadedAt() {
			return loadedAt;
		},
		get selected() {
			return items[0] ?? null;
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
				loadedAt = Date.now();
			} catch (e) {
				error = message(e, 'Connectors not loaded');
			} finally {
				isLoading = false;
			}
		},

		async loadQueue(id: string, projectId: string, params: CandidateQuery = {}, quiet = false) {
			const seq = ++queueSeq;
			if (!quiet) {
				queueLoading = true;
				queueError = null;
			}
			try {
				const next = await connectorsApi.candidates(id, projectId, params);
				if (seq !== queueSeq) return;
				queue = next;
				queueError = null;
			} catch (e) {
				if (seq === queueSeq) queueError = message(e, 'Requests not loaded');
			} finally {
				if (seq === queueSeq) queueLoading = false;
			}
		},

		async loadDiscovered(id: string, projectId: string) {
			try {
				discovered = await connectorsApi.discovered(id, projectId);
				discoveredError = null;
			} catch (e) {
				discoveredError = message(e, 'Domains not loaded');
			}
		},

		upsert(connector: Connector) {
			const at = items.findIndex((c) => c.id === connector.id);
			if (at >= 0) items[at] = connector;
			else items = [connector, ...items];
		},

		drop(id: string) {
			items = items.filter((c) => c.id !== id);
			queueSeq++;
			queue = null;
			queueLoading = false;
			queueError = null;
			discovered = [];
			discoveredError = null;
		},

		reset() {
			catalog = [];
			items = [];
			queueSeq++;
			queue = null;
			discovered = [];
			isLoading = false;
			queueLoading = false;
			error = null;
			queueError = null;
			discoveredError = null;
			fetchedProjectId = null;
			loadedAt = 0;
		}
	};
}

export const connectors = createConnectorsStore();
