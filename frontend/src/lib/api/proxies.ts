import { api } from './client';
import { crudApi } from './crud';
import type { ProxyRead, ProxyCreate, ProxyUpdate, ProxyTestResult } from '$lib/types/proxy';

export const proxiesApi = {
	...crudApi<ProxyRead, ProxyCreate, ProxyUpdate, ProxyTestResult>('/proxies'),

	setDefault: (id: string): Promise<ProxyRead> => {
		return api.post<ProxyRead>(`/proxies/${id}/set-default`);
	}
};
