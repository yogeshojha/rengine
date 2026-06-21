import { api } from './client';
import type { ProxyRead, ProxyCreate, ProxyUpdate, ProxyTestResult } from '$lib/types/proxy';

export const proxiesApi = {
	list: (): Promise<ProxyRead[]> => {
		return api.get<ProxyRead[]>('/proxies');
	},

	get: (id: string): Promise<ProxyRead> => {
		return api.get<ProxyRead>(`/proxies/${id}`);
	},

	create: (data: ProxyCreate): Promise<ProxyRead> => {
		return api.post<ProxyRead>('/proxies', data);
	},

	update: (id: string, data: ProxyUpdate): Promise<ProxyRead> => {
		return api.patch<ProxyRead>(`/proxies/${id}`, data);
	},

	remove: (id: string): Promise<void> => {
		return api.delete(`/proxies/${id}`);
	},

	test: (id: string): Promise<ProxyTestResult> => {
		return api.post<ProxyTestResult>(`/proxies/${id}/test`);
	},

	setDefault: (id: string): Promise<ProxyRead> => {
		return api.post<ProxyRead>(`/proxies/${id}/set-default`);
	}
};
