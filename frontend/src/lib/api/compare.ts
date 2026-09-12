import { api } from './client';
import type { ChangeRows, ChangeVerb, ComparableRun, ScanComparison } from '$lib/types/compare';

interface RowParams {
	projectId: string;
	current: string;
	baseline?: string | null;
	dimension?: string;
	verbs?: ChangeVerb[];
	page?: number;
	size?: number;
}

function base(projectId: string, current: string, baseline?: string | null): URLSearchParams {
	const sp = new URLSearchParams({ project_id: projectId, current });
	if (baseline) sp.set('baseline', baseline);
	return sp;
}

export const compareApi = {
	async comparison(
		projectId: string,
		current: string,
		baseline?: string | null
	): Promise<ScanComparison> {
		return api.get<ScanComparison>(`/scans/compare?${base(projectId, current, baseline)}`);
	},

	async rows(params: RowParams): Promise<ChangeRows> {
		const sp = base(params.projectId, params.current, params.baseline);
		if (params.dimension) sp.set('dimension', params.dimension);
		for (const verb of params.verbs ?? []) sp.append('verb', verb);
		if (params.page) sp.set('page', String(params.page));
		if (params.size) sp.set('size', String(params.size));
		return api.get<ChangeRows>(`/scans/compare/rows?${sp}`);
	},

	async diff(params: Omit<RowParams, 'page' | 'size'>): Promise<string> {
		const sp = base(params.projectId, params.current, params.baseline);
		if (params.dimension) sp.set('dimension', params.dimension);
		for (const verb of params.verbs ?? []) sp.append('verb', verb);
		return api.text(`/scans/compare/diff?${sp}`);
	},

	async comparable(projectId: string, scanId: string): Promise<ComparableRun[]> {
		return api.get<ComparableRun[]>(`/scans/${scanId}/comparable?project_id=${projectId}`);
	}
};
