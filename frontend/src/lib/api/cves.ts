import { api } from './client';
import type { CveExposure, CveIndex } from '$lib/types/cve';

export interface CveIndexQuery {
	q?: string;
	page?: number;
	size?: number;
	sort?: string;
	dir?: 'asc' | 'desc';
	severity?: string | null;
	kev?: boolean;
	ransomware?: boolean;
	evidence?: string[];
}

export const cvesApi = {
	async index(projectId: string, options: CveIndexQuery = {}): Promise<CveIndex> {
		const params = new URLSearchParams({ project_id: projectId });
		if (options.q) params.set('q', options.q);
		if (options.page) params.set('page', String(options.page));
		if (options.size) params.set('size', String(options.size));
		if (options.sort) params.set('sort', options.sort);
		if (options.dir) params.set('dir', options.dir);
		if (options.severity) params.set('severity', options.severity);
		if (options.kev) params.set('kev', 'true');
		if (options.ransomware) params.set('ransomware', 'true');
		for (const rung of options.evidence ?? []) params.append('evidence', rung);
		return api.get<CveIndex>(`/cves?${params.toString()}`);
	},

	async exposure(projectId: string, cve: string): Promise<CveExposure> {
		return api.get<CveExposure>(
			`/cves/${encodeURIComponent(cve)}?project_id=${encodeURIComponent(projectId)}`
		);
	}
};
