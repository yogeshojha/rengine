import { api } from './client';
import type { QueryGroups, QueryLeads } from '$lib/types/asset-query';
import type {
	BulkTriageResult,
	CoverageRead,
	IssuePage,
	ScanVulnerabilities,
	TriageResult,
	VulnFacetSet,
	VulnFilter,
	VulnSearchResult,
	VulnerabilityRead
} from '$lib/utilities/vulns';
import type {
	SelectionPreview,
	TemplateFilter,
	TemplateLibraryStats,
	TemplatePage,
	TemplateSelection,
	TemplateSource,
	TemplateSyncResult,
	VulnTemplateRead,
	VulnTemplateUploadResult
} from '$lib/types/vuln-template';

export const vulnerabilitiesApi = {
	async search(scanId: string, filter: VulnFilter): Promise<VulnSearchResult> {
		return api.post<VulnSearchResult>(`/vulnerabilities/search?scan_id=${scanId}`, filter);
	},

	async issues(scanId: string, filter: VulnFilter): Promise<IssuePage> {
		return api.post<IssuePage>(`/vulnerabilities/search/issues?scan_id=${scanId}`, filter);
	},

	async triageMany(
		scanId: string,
		body: { fingerprints?: string[]; template_ids?: string[]; state: string; note?: string | null }
	): Promise<BulkTriageResult> {
		return api.post<BulkTriageResult>(`/vulnerabilities/triage/bulk?scan_id=${scanId}`, body);
	},

	async leads(scanId: string, filter: VulnFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(`/vulnerabilities/search/leads?scan_id=${scanId}`, filter);
	},

	async groups(scanId: string, groupBy: string, filter: VulnFilter): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/vulnerabilities/search/groups?scan_id=${scanId}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async facets(scanId: string): Promise<VulnFacetSet> {
		return api.get<VulnFacetSet>(`/vulnerabilities/facets?scan_id=${scanId}`);
	},

	async overview(scanId: string): Promise<ScanVulnerabilities> {
		return api.get<ScanVulnerabilities>(`/vulnerabilities/overview?scan_id=${scanId}`);
	},

	async coverage(scanId: string): Promise<CoverageRead[]> {
		return api.get<CoverageRead[]>(`/vulnerabilities/coverage?scan_id=${scanId}`);
	},

	async detail(scanId: string, id: string): Promise<VulnerabilityRead> {
		return api.get<VulnerabilityRead>(`/vulnerabilities/${id}?scan_id=${scanId}`);
	},

	async triage(
		scanId: string,
		fingerprint: string,
		state: string,
		note: string | null
	): Promise<TriageResult> {
		return api.patch<TriageResult>(`/vulnerabilities/triage/${fingerprint}?scan_id=${scanId}`, {
			state,
			note
		});
	}
};

export const vulnTemplatesApi = {
	async stats(): Promise<TemplateLibraryStats> {
		return api.get<TemplateLibraryStats>('/vuln-templates/stats');
	},

	async search(filter: TemplateFilter): Promise<TemplatePage> {
		return api.post<TemplatePage>('/vuln-templates/search', filter);
	},

	async selection(selection: TemplateSelection): Promise<SelectionPreview> {
		return api.post<SelectionPreview>('/vuln-templates/selection', selection);
	},

	async sync(): Promise<TemplateSyncResult> {
		return api.post<TemplateSyncResult>('/vuln-templates/sync', {});
	},

	async upload(files: { filename: string; content: string }[]): Promise<VulnTemplateUploadResult> {
		return api.post<VulnTemplateUploadResult>('/vuln-templates/upload', { files });
	},

	async get(id: string): Promise<VulnTemplateRead> {
		return api.get<VulnTemplateRead>(`/vuln-templates/${id}`);
	},

	async update(id: string, enabled: boolean): Promise<VulnTemplateRead> {
		return api.patch<VulnTemplateRead>(`/vuln-templates/${id}`, { enabled });
	},

	async source(id: string): Promise<TemplateSource> {
		return api.get<TemplateSource>(`/vuln-templates/${id}/source`);
	},

	async saveSource(id: string, content: string): Promise<VulnTemplateRead> {
		return api.put<VulnTemplateRead>(`/vuln-templates/${id}/source`, { content });
	},

	async remove(id: string): Promise<void> {
		return api.delete<void>(`/vuln-templates/${id}`);
	}
};
