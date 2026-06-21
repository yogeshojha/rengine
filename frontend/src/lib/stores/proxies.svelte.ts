import { proxiesApi } from '$lib/api/proxies';
import type { ProxyRead, ProxyCreate, ProxyUpdate, ProxyTestResult } from '$lib/types/proxy';
import { toast } from 'svelte-sonner';

function createProxiesStore() {
	let proxies = $state<ProxyRead[]>([]);
	let isLoading = $state(false);
	let hasFetched = $state(false);

	return {
		get proxies() {
			return proxies;
		},
		get isLoading() {
			return isLoading;
		},
		get hasFetched() {
			return hasFetched;
		},

		async fetch() {
			if (isLoading) return;
			isLoading = true;
			try {
				proxies = await proxiesApi.list();
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to fetch proxies');
			} finally {
				isLoading = false;
			}
		},

		async create(data: ProxyCreate): Promise<ProxyRead | null> {
			try {
				const created = await proxiesApi.create(data);
				proxies = [...proxies, created];
				return created;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to create proxy');
				return null;
			}
		},

		async update(id: string, data: ProxyUpdate): Promise<ProxyRead | null> {
			try {
				const updated = await proxiesApi.update(id, data);
				proxies = proxies.map((p) => (p.id === id ? updated : p));
				return updated;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to update proxy');
				return null;
			}
		},

		async remove(id: string): Promise<boolean> {
			try {
				await proxiesApi.remove(id);
				proxies = proxies.filter((p) => p.id !== id);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to delete proxy');
				return false;
			}
		},

		async test(id: string): Promise<ProxyTestResult | null> {
			try {
				const result = await proxiesApi.test(id);
				proxies = proxies.map((p) =>
					p.id === id
						? {
								...p,
								last_test_at: new Date().toISOString(),
								last_test_ok: result.success,
								last_test_message: result.message
							}
						: p
				);
				return result;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to test proxy');
				return null;
			}
		},

		async setDefault(id: string): Promise<ProxyRead | null> {
			try {
				const updated = await proxiesApi.setDefault(id);
				proxies = proxies.map((p) => ({ ...p, is_default: p.id === id }));
				return updated;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to set default proxy');
				return null;
			}
		},

		clear() {
			proxies = [];
			hasFetched = false;
		}
	};
}

export const proxiesStore = createProxiesStore();
