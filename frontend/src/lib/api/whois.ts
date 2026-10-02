import { api } from './client';
import type {
	WhoisRecordRead,
	WhoisCorrelationResult,
	WhoisRefreshResponse
} from '$lib/types/whois';

export const whoisApi = {
	async getRecord(recordId: string): Promise<WhoisRecordRead> {
		return api.get<WhoisRecordRead>(`/tools/whois/records/${recordId}`);
	},

	async refreshRecord(recordId: string): Promise<WhoisRefreshResponse> {
		return api.post<WhoisRefreshResponse>(`/tools/whois/records/${recordId}/refresh`);
	},

	async getTargetCorrelations(targetId: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(`/tools/whois/correlations/target/${targetId}`);
	},

	async getTargetsCorrelations(
		targetIds: string[]
	): Promise<Record<string, WhoisCorrelationResult[]>> {
		const ids = encodeURIComponent(targetIds.join(','));
		return api.get<Record<string, WhoisCorrelationResult[]>>(
			`/tools/whois/correlations/targets?ids=${ids}`
		);
	},

	async correlateByRegistrant(name: string, projectId: string): Promise<WhoisCorrelationResult[]> {
		const params = new URLSearchParams({ name, project_id: projectId });
		return api.get<WhoisCorrelationResult[]>(`/tools/whois/correlations/registrant?${params}`);
	},

	async correlateByRegistrar(name: string, projectId: string): Promise<WhoisCorrelationResult[]> {
		const params = new URLSearchParams({ name, project_id: projectId });
		return api.get<WhoisCorrelationResult[]>(`/tools/whois/correlations/registrar?${params}`);
	},

	async correlateByNetwork(cidr: string, projectId: string): Promise<WhoisCorrelationResult[]> {
		const params = new URLSearchParams({ cidr, project_id: projectId });
		return api.get<WhoisCorrelationResult[]>(`/tools/whois/correlations/network?${params}`);
	},

	async correlateByNameserver(ns: string, projectId: string): Promise<WhoisCorrelationResult[]> {
		const params = new URLSearchParams({ ns, project_id: projectId });
		return api.get<WhoisCorrelationResult[]>(`/tools/whois/correlations/nameserver?${params}`);
	}
};
