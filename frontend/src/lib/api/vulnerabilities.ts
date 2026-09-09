import { api } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
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
	async search(projectId: string, scanId: string, filter: VulnFilter): Promise<VulnSearchResult> {
		return api.post<VulnSearchResult>(
			`/vulnerabilities/search?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async issues(projectId: string, scanId: string, filter: VulnFilter): Promise<IssuePage> {
		return api.post<IssuePage>(
			`/vulnerabilities/search/issues?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async triageMany(
		projectId: string,
		scanId: string,
		body: { fingerprints?: string[]; template_ids?: string[]; state: string; note?: string | null }
	): Promise<BulkTriageResult> {
		return api.post<BulkTriageResult>(
			`/vulnerabilities/triage/bulk?${scopeQuery({ projectId, scanId })}`,
			body
		);
	},

	async leads(projectId: string, scanId: string, filter: VulnFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(
			`/vulnerabilities/search/leads?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: VulnFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/vulnerabilities/search/groups?${scopeQuery({ projectId, scanId })}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string): Promise<VulnFacetSet> {
		return api.get<VulnFacetSet>(`/vulnerabilities/facets?${scopeQuery({ projectId, scanId })}`);
	},

	async overview(projectId: string, scanId: string): Promise<ScanVulnerabilities> {
		return api.get<ScanVulnerabilities>(
			`/vulnerabilities/overview?${scopeQuery({ projectId, scanId })}`
		);
	},

	async coverage(projectId: string, scanId: string): Promise<CoverageRead[]> {
		return api.get<CoverageRead[]>(
			`/vulnerabilities/coverage?${scopeQuery({ projectId, scanId })}`
		);
	},

	async detail(projectId: string, scanId: string, id: string): Promise<VulnerabilityRead> {
		return api.get<VulnerabilityRead>(
			`/vulnerabilities/${id}?${scopeQuery({ projectId, scanId })}`
		);
	},

	async triage(
		projectId: string,
		scanId: string,
		fingerprint: string,
		state: string,
		note: string | null
	): Promise<TriageResult> {
		return api.patch<TriageResult>(
			`/vulnerabilities/triage/${fingerprint}?${scopeQuery({ projectId, scanId })}`,
			{
				state,
				note
			}
		);
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
