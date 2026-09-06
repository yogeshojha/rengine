import { api, API_PREFIX } from './client';
import type {
	Report,
	ReportCatalog,
	ReportCreate,
	ReportEstimate,
	ReportTemplate,
	ReportTheme
} from '$lib/types/report';

function q(params: Record<string, string | undefined>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) if (value) search.set(key, value);
	const text = search.toString();
	return text ? `?${text}` : '';
}

export const reportsApi = {
	catalog(): Promise<ReportCatalog> {
		return api.get<ReportCatalog>('/reports/catalog');
	},

	templates(projectId: string): Promise<ReportTemplate[]> {
		return api.get<ReportTemplate[]>(`/reports/templates${q({ project_id: projectId })}`);
	},

	createTemplate(projectId: string, body: unknown): Promise<ReportTemplate> {
		return api.post<ReportTemplate>(`/reports/templates${q({ project_id: projectId })}`, body);
	},

	updateTemplate(projectId: string, id: string, body: unknown): Promise<ReportTemplate> {
		return api.patch<ReportTemplate>(
			`/reports/templates/${id}${q({ project_id: projectId })}`,
			body
		);
	},

	deleteTemplate(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/reports/templates/${id}${q({ project_id: projectId })}`);
	},

	list(projectId: string, opts: { scanId?: string; targetId?: string } = {}): Promise<Report[]> {
		return api.get<Report[]>(
			`/reports${q({ project_id: projectId, scan_id: opts.scanId, target_id: opts.targetId })}`
		);
	},

	get(projectId: string, id: string): Promise<Report> {
		return api.get<Report>(`/reports/${id}${q({ project_id: projectId })}`);
	},

	create(projectId: string, body: ReportCreate): Promise<Report> {
		return api.post<Report>(`/reports${q({ project_id: projectId })}`, body);
	},

	estimate(projectId: string, body: ReportCreate): Promise<ReportEstimate> {
		return api.post<ReportEstimate>(`/reports/estimate${q({ project_id: projectId })}`, body);
	},

	retry(projectId: string, id: string): Promise<Report> {
		return api.post<Report>(`/reports/${id}/retry${q({ project_id: projectId })}`);
	},

	remove(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/reports/${id}${q({ project_id: projectId })}`);
	},

	downloadUrl(projectId: string, id: string, format: string): string {
		return `${API_PREFIX}/reports/${id}/download${q({ project_id: projectId, format })}`;
	},

	themes(): Promise<ReportTheme[]> {
		return api.get<ReportTheme[]>('/reports/themes');
	},

	themeSource(slug: string): Promise<string> {
		return api.get<string>(`/reports/themes/${slug}/source`);
	},

	uploadTheme(content: string, filename = ''): Promise<ReportTheme> {
		return api.post<ReportTheme>('/reports/themes', { content, filename });
	},

	deleteTheme(slug: string): Promise<void> {
		return api.delete<void>(`/reports/themes/${slug}`);
	}
};
