import { toast } from 'svelte-sonner';
import { proxiesApi } from '$lib/api/proxies';
import { createCrudStore } from '$lib/stores/crud.svelte';
import type { ProxyRead } from '$lib/types/proxy';
import { errorMessage } from '$lib/utilities/errors';

function createProxiesStore() {
	const store = createCrudStore(proxiesApi, {
		notLoaded: 'Proxies not loaded',
		notCreated: 'Proxy not created',
		notSaved: 'Proxy not saved',
		notDeleted: 'Proxy not deleted',
		testFailed: 'Proxy test failed'
	});

	return Object.assign(store, {
		async setDefault(id: string): Promise<ProxyRead | null> {
			try {
				const updated = await proxiesApi.setDefault(id);
				store.patchAll((p) => ({ ...p, is_default: p.id === id }));
				return updated;
			} catch (e) {
				toast.error(errorMessage(e, 'Default proxy not set'));
				return null;
			}
		}
	});
}

export const proxiesStore = createProxiesStore();
