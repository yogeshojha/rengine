import { api, API_PREFIX, toQuery } from './client';
import type {
	Report,
	ReportCatalog,
	ReportDefaults,
	ReportFont,
	ReportFontUpload,
	ReportCreate,
	ReportEstimate,
	ReportTemplate,
	ReportTheme
} from '$lib/types/report';

export const reportsApi = {
	catalog(): Promise<ReportCatalog> {
		return api.get<ReportCatalog>('/reports/catalog');
	},

	templates(projectId: string): Promise<ReportTemplate[]> {
		return api.get<ReportTemplate[]>(`/reports/templates${toQuery({ project_id: projectId })}`);
	},

	createTemplate(projectId: string, body: unknown): Promise<ReportTemplate> {
		return api.post<ReportTemplate>(
			`/reports/templates${toQuery({ project_id: projectId })}`,
			body
		);
	},

	updateTemplate(projectId: string, id: string, body: unknown): Promise<ReportTemplate> {
		return api.patch<ReportTemplate>(
			`/reports/templates/${id}${toQuery({ project_id: projectId })}`,
			body
		);
	},

	deleteTemplate(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/reports/templates/${id}${toQuery({ project_id: projectId })}`);
	},

	list(projectId: string): Promise<Report[]> {
		return api.get<Report[]>(`/reports${toQuery({ project_id: projectId })}`);
	},

	get(projectId: string, id: string): Promise<Report> {
		return api.get<Report>(`/reports/${id}${toQuery({ project_id: projectId })}`);
	},

	create(projectId: string, body: ReportCreate): Promise<Report> {
		return api.post<Report>(`/reports${toQuery({ project_id: projectId })}`, body);
	},

	estimate(projectId: string, body: ReportCreate): Promise<ReportEstimate> {
		return api.post<ReportEstimate>(`/reports/estimate${toQuery({ project_id: projectId })}`, body);
	},

	retry(projectId: string, id: string): Promise<Report> {
		return api.post<Report>(`/reports/${id}/retry${toQuery({ project_id: projectId })}`);
	},

	remove(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/reports/${id}${toQuery({ project_id: projectId })}`);
	},

	downloadUrl(projectId: string, id: string, format: string): string {
		return `${API_PREFIX}/reports/${id}/download${toQuery({ project_id: projectId, format })}`;
	},

	previewUrl(projectId: string, id: string): string {
		return `${API_PREFIX}/reports/${id}/preview${toQuery({ project_id: projectId })}`;
	},

	pdf(projectId: string, id: string): Promise<ArrayBuffer> {
		return api.bytes(`/reports/${id}/preview${toQuery({ project_id: projectId })}`);
	},

	uploadFont(body: ReportFontUpload): Promise<ReportFont> {
		return api.post<ReportFont>('/reports/fonts', body);
	},

	deleteFont(slug: string): Promise<void> {
		return api.delete<void>(`/reports/fonts/${slug}`);
	},

	defaults(): Promise<ReportDefaults> {
		return api.get<ReportDefaults>('/reports/defaults');
	},

	saveDefaults(body: ReportDefaults): Promise<ReportDefaults> {
		return api.put<ReportDefaults>('/reports/defaults', body);
	},

	themeSource(slug: string): Promise<string> {
		return api.get<string>(`/reports/themes/${slug}/source`);
	},

	uploadTheme(content: string): Promise<ReportTheme> {
		return api.post<ReportTheme>('/reports/themes', { content });
	},

	deleteTheme(slug: string): Promise<void> {
		return api.delete<void>(`/reports/themes/${slug}`);
	}
};
