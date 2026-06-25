import { api } from './client';
import type { HttpAssetRead, HttpAssetSummary } from '$lib/types/http-asset';
import type { IpAddressRead, IpAddressSummary } from '$lib/types/ip-address';
import type { PortRead, PortSummary } from '$lib/types/port';

interface ListParams {
	search?: string;
	limit?: number;
	offset?: number;
}

function buildQuery(base: Record<string, string>, params: ListParams): string {
	const sp = new URLSearchParams(base);
	if (params.search) sp.append('search', params.search);
	if (params.limit != null) sp.append('limit', String(params.limit));
	if (params.offset != null) sp.append('offset', String(params.offset));
	return sp.toString();
}

export const httpAssetsApi = {
	async listByScan(
		projectId: string,
		scanId: string,
		params: ListParams = {}
	): Promise<HttpAssetRead[]> {
		const q = buildQuery({ project_id: projectId, scan_id: scanId }, params);
		return api.get<HttpAssetRead[]>(`/http-assets?${q}`);
	},

	async scanSummary(projectId: string, scanId: string): Promise<HttpAssetSummary> {
		return api.get<HttpAssetSummary>(
			`/http-assets/summary?project_id=${projectId}&scan_id=${scanId}`
		);
	}
};

export const portsApi = {
	async listByScan(
		projectId: string,
		scanId: string,
		params: ListParams = {}
	): Promise<PortRead[]> {
		const q = buildQuery({ project_id: projectId, scan_id: scanId }, params);
		return api.get<PortRead[]>(`/ports?${q}`);
	},

	async scanSummary(projectId: string, scanId: string): Promise<PortSummary> {
		return api.get<PortSummary>(`/ports/summary?project_id=${projectId}&scan_id=${scanId}`);
	}
};

export const ipsApi = {
	async listByScan(
		projectId: string,
		scanId: string,
		params: ListParams = {}
	): Promise<IpAddressRead[]> {
		const q = buildQuery({ project_id: projectId, scan_id: scanId }, params);
		return api.get<IpAddressRead[]>(`/ips?${q}`);
	},

	async scanSummary(projectId: string, scanId: string): Promise<IpAddressSummary> {
		return api.get<IpAddressSummary>(`/ips/summary?project_id=${projectId}&scan_id=${scanId}`);
	}
};
