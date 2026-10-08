import { SvelteSet } from 'svelte/reactivity';
import { aiApi } from '$lib/api/ai';
import { forgetBriefs } from '$lib/api/ask';
import type {
	AiCallPage,
	AiCatalog,
	AiConnection,
	AiConnectionCreate,
	AiConnectionUpdate,
	AiModelList,
	AiModelsRequest,
	AiProvider,
	AiSettingsUpdate,
	AiStatus,
	AiTestRequest,
	AiTestResult
} from '$lib/types/ai';
import { toast } from 'svelte-sonner';

const MODEL_LIST_TTL_MS = 60_000;

function failure(e: unknown, fallback: string): string {
	return e instanceof Error ? e.message : fallback;
}

function askSignature(s: AiStatus | null): string {
	if (!s) return '';
	return JSON.stringify([s.enabled, s.configured, s.connection_id, s.model, s.features]);
}

function createAiStore() {
	let status = $state<AiStatus | null>(null);
	let catalog = $state<AiCatalog | null>(null);
	let connections = $state<AiConnection[]>([]);
	let isLoading = $state(false);
	let isSaving = $state(false);
	let hasFetched = $state(false);
	let loadError = $state<string | null>(null);
	const testing = new SvelteSet<string>();
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const modelLists = new Map<string, { at: number; list: Promise<AiModelList> }>();

	function adopt(next: AiStatus) {
		if (status && askSignature(status) !== askSignature(next)) forgetBriefs();
		status = next;
	}

	function merge(row: AiConnection) {
		const rest = connections.map((c) =>
			row.in_use && c.id !== row.id ? { ...c, in_use: false } : c
		);
		connections = rest.some((c) => c.id === row.id)
			? rest.map((c) => (c.id === row.id ? row : c))
			: [...rest, row];
	}

	async function refreshStatus() {
		const next = await aiApi.status().catch(() => null);
		if (next) adopt(next);
	}

	async function testConnection(id: string): Promise<AiTestResult | null> {
		testing.add(id);
		try {
			const result = await aiApi.testConnection(id);
			connections = connections.map((c) =>
				c.id === id
					? {
							...c,
							last_test_at: new Date().toISOString(),
							last_test_ok: result.success,
							last_test_message: result.message
						}
					: c
			);
			void refreshStatus();
			return result;
		} catch (e) {
			toast.error(failure(e, 'Test not run'));
			return null;
		} finally {
			testing.delete(id);
		}
	}

	async function check(id: string) {
		const result = await testConnection(id);
		if (result && !result.success) toast.error(result.message);
	}

	function settle(row: AiConnection) {
		merge(row);
		if (row.in_use && !row.last_test_at) void check(row.id);
	}

	return {
		get status() {
			return status;
		},
		get catalog() {
			return catalog;
		},
		get connections() {
			return connections;
		},
		get isLoading() {
			return isLoading;
		},
		get isSaving() {
			return isSaving;
		},
		get hasFetched() {
			return hasFetched;
		},
		/** Why the settings did not load; the page shows it inline (no toast). */
		get loadError() {
			return loadError;
		},

		isTesting(id: string): boolean {
			return testing.has(id);
		},

		provider(key: string | null | undefined): AiProvider | undefined {
			return catalog?.providers.find((p) => p.key === key);
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			try {
				const [s, c, rows] = await Promise.all([
					aiApi.status(),
					aiApi.catalog(),
					aiApi.connections()
				]);
				adopt(s);
				catalog = c;
				connections = rows;
				hasFetched = true;
				loadError = null;
			} catch (e) {
				loadError = failure(e, 'AI settings not loaded');
			} finally {
				isLoading = false;
			}
		},

		refreshStatus,

		async save(body: AiSettingsUpdate): Promise<boolean> {
			isSaving = true;
			try {
				adopt(await aiApi.update(body));
				return true;
			} catch (e) {
				toast.error(failure(e, 'AI settings not saved'));
				return false;
			} finally {
				isSaving = false;
			}
		},

		async create(body: AiConnectionCreate): Promise<AiConnection | null> {
			isSaving = true;
			try {
				const row = await aiApi.createConnection(body);
				settle(row);
				await refreshStatus();
				return row;
			} catch (e) {
				toast.error(failure(e, 'Provider not saved'));
				return null;
			} finally {
				isSaving = false;
			}
		},

		async update(id: string, body: AiConnectionUpdate): Promise<AiConnection | null> {
			isSaving = true;
			try {
				const row = await aiApi.updateConnection(id, body);
				settle(row);
				await refreshStatus();
				return row;
			} catch (e) {
				toast.error(failure(e, 'Provider not saved'));
				return null;
			} finally {
				isSaving = false;
			}
		},

		async remove(id: string): Promise<boolean> {
			try {
				await aiApi.deleteConnection(id);
				connections = connections.filter((c) => c.id !== id);
				await refreshStatus();
				return true;
			} catch (e) {
				toast.error(failure(e, 'Provider not removed'));
				return false;
			}
		},

		async use(id: string): Promise<boolean> {
			const before = connections;
			connections = connections.map((c) => ({ ...c, in_use: c.id === id }));
			try {
				merge(await aiApi.useConnection(id));
				await refreshStatus();
				void check(id);
				return true;
			} catch (e) {
				connections = before;
				toast.error(failure(e, 'Provider not switched'));
				return false;
			}
		},

		testConnection,
		check,

		async test(body: AiTestRequest): Promise<AiTestResult | null> {
			try {
				return await aiApi.test(body);
			} catch (e) {
				toast.error(failure(e, 'Test not run'));
				return null;
			}
		},

		listModels(body: AiModelsRequest, force = false): Promise<AiModelList> {
			const key = JSON.stringify(body);
			const hit = modelLists.get(key);
			if (!force && hit && Date.now() - hit.at < MODEL_LIST_TTL_MS) return hit.list;
			const list = aiApi.models(body);
			modelLists.set(key, { at: Date.now(), list });
			list.then(
				(result) => {
					if (result.error) modelLists.delete(key);
				},
				() => modelLists.delete(key)
			);
			return list;
		},

		calls(limit: number, before?: string): Promise<AiCallPage> {
			return aiApi.calls(limit, before);
		},

		async clearCache(): Promise<number | null> {
			try {
				const result = await aiApi.clearCache();
				if (status) status = { ...status, cached_narratives: 0 };
				return result.removed;
			} catch (e) {
				toast.error(failure(e, 'Cache not cleared'));
				return null;
			}
		},

		reset() {
			status = null;
			catalog = null;
			connections = [];
			isLoading = false;
			isSaving = false;
			hasFetched = false;
			loadError = null;
			testing.clear();
			modelLists.clear();
		}
	};
}

export const ai = createAiStore();
