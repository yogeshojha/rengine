import { api } from './client';
import type {
	WhoisRecordRead,
	WhoisCorrelationResult,
	WhoisRefreshResponse,
	WhoisLookupRequest,
	WhoisLookupResponse,
	WhoisRecordSummary
} from '$lib/types/whois';
import type { PaginatedResponse } from '$lib/types/pagination';

interface ListWhoisParams {
	lookup_type?: string;
	registrant_name?: string;
	registrar_name?: string;
	country?: string;
	page?: number;
	size?: number;
}

export const whoisApi = {
	async lookup(data: WhoisLookupRequest): Promise<WhoisLookupResponse> {
		return api.post<WhoisLookupResponse>('/tools/whois/lookup', data);
	},

	async listRecords(params?: ListWhoisParams): Promise<PaginatedResponse<WhoisRecordSummary>> {
		const searchParams = new URLSearchParams();
		if (params?.lookup_type) searchParams.append('lookup_type', params.lookup_type);
		if (params?.registrant_name) searchParams.append('registrant_name', params.registrant_name);
		if (params?.registrar_name) searchParams.append('registrar_name', params.registrar_name);
		if (params?.country) searchParams.append('country', params.country);
		if (params?.page) searchParams.append('page', params.page.toString());
		if (params?.size) searchParams.append('size', params.size.toString());

		const query = searchParams.toString();
		return api.get<PaginatedResponse<WhoisRecordSummary>>(
			query ? `/tools/whois/records?${query}` : '/tools/whois/records'
		);
	},

	async getRecord(recordId: string): Promise<WhoisRecordRead> {
		return api.get<WhoisRecordRead>(`/tools/whois/records/${recordId}`);
	},

	async getRecordByTarget(targetId: string): Promise<WhoisRecordRead | null> {
		return api.get<WhoisRecordRead | null>(`/tools/whois/records/by-target/${targetId}`);
	},

	async refreshRecord(recordId: string): Promise<WhoisRefreshResponse> {
		return api.post<WhoisRefreshResponse>(`/tools/whois/records/${recordId}/refresh`);
	},

	async deleteRecord(recordId: string): Promise<void> {
		return api.delete(`/tools/whois/records/${recordId}`);
	},

	async getTargetCorrelations(targetId: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(`/tools/whois/correlations/target/${targetId}`);
	},

	async correlateByRegistrant(name: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(
			`/tools/whois/correlations/registrant?name=${encodeURIComponent(name)}`
		);
	},

	async correlateByRegistrar(name: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(
			`/tools/whois/correlations/registrar?name=${encodeURIComponent(name)}`
		);
	},

	async correlateByNetwork(cidr: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(
			`/tools/whois/correlations/network?cidr=${encodeURIComponent(cidr)}`
		);
	},

	async correlateByCountry(code: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(
			`/tools/whois/correlations/country?code=${encodeURIComponent(code)}`
		);
	},

	async correlateByNameserver(ns: string): Promise<WhoisCorrelationResult[]> {
		return api.get<WhoisCorrelationResult[]>(
			`/tools/whois/correlations/nameserver?ns=${encodeURIComponent(ns)}`
		);
	}
};
