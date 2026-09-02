import { api } from './client';
import type {
	ScanActivityRead,
	ScanBatchCreate,
	ScanChanges,
	ScanChangeWindow,
	ScanCommandDetail,
	ScanCommandRead,
	ScanCreate,
	ScanExportRow,
	ScanPreview,
	ScanRead,
	ScanSortDir,
	ScanSortKey,
	ScanStats,
	ScanStatus,
	ScanTargetGroup,
	ScanTimeRange
} from '$lib/types/scan';
import type { PaginatedResponse } from '$lib/types/pagination';

interface ScanFilterParams {
	target_id?: string;
	status?: ScanStatus[];
	engine?: string[];
	context?: string[];
	search?: string;
	time_range?: ScanTimeRange;
	sort_by?: ScanSortKey;
	sort_dir?: ScanSortDir;
	scheduled?: boolean | null;
}

interface ListScansParams extends ScanFilterParams {
	page?: number;
	size?: number;
}

function buildScanQuery(projectId: string, params: ScanFilterParams): URLSearchParams {
	const sp = new URLSearchParams({ project_id: projectId });
	if (params.target_id) sp.append('target_id', params.target_id);
	for (const s of params.status ?? []) sp.append('status', s);
	for (const e of params.engine ?? []) sp.append('engine', e);
	for (const c of params.context ?? []) sp.append('context', c);
	if (params.search?.trim()) sp.append('search', params.search.trim());
	if (params.time_range && params.time_range !== 'all') sp.append('time_range', params.time_range);
	if (params.sort_by) sp.append('sort_by', params.sort_by);
	if (params.sort_dir) sp.append('sort_dir', params.sort_dir);
	if (params.scheduled != null) sp.append('scheduled', String(params.scheduled));
	return sp;
}

export const scansApi = {
	async preview(projectId: string, body: ScanCreate): Promise<ScanPreview> {
		return api.post<ScanPreview>(`/scans/preview?project_id=${projectId}`, body);
	},

	async launchBatch(projectId: string, body: ScanBatchCreate): Promise<ScanRead[]> {
		return api.post<ScanRead[]>(`/scans/batch?project_id=${projectId}`, body);
	},

	async list(
		projectId: string,
		params: ListScansParams = {}
	): Promise<PaginatedResponse<ScanRead>> {
		const sp = buildScanQuery(projectId, params);
		if (params.page) sp.append('page', String(params.page));
		if (params.size) sp.append('size', String(params.size));
		return api.get<PaginatedResponse<ScanRead>>(`/scans?${sp.toString()}`);
	},

	async exportRows(projectId: string, params: ScanFilterParams = {}): Promise<ScanExportRow[]> {
		const sp = buildScanQuery(projectId, params);
		return api.get<ScanExportRow[]>(`/scans/export?${sp.toString()}`);
	},

	async listTargets(
		projectId: string,
		params: ListScansParams = {}
	): Promise<PaginatedResponse<ScanTargetGroup>> {
		const sp = buildScanQuery(projectId, params);
		if (params.page) sp.append('page', String(params.page));
		if (params.size) sp.append('size', String(params.size));
		return api.get<PaginatedResponse<ScanTargetGroup>>(`/scans/targets?${sp.toString()}`);
	},

	async stats(projectId: string, targetId?: string): Promise<ScanStats> {
		const sp = new URLSearchParams({ project_id: projectId });
		if (targetId) sp.append('target_id', targetId);
		return api.get<ScanStats>(`/scans/stats?${sp.toString()}`);
	},

	async changes(
		projectId: string,
		window: ScanChangeWindow,
		targetId?: string
	): Promise<ScanChanges> {
		const sp = new URLSearchParams({ project_id: projectId, window });
		if (targetId) sp.append('target_id', targetId);
		return api.get<ScanChanges>(`/scans/changes?${sp.toString()}`);
	},

	async get(id: string, projectId: string): Promise<ScanRead> {
		return api.get<ScanRead>(`/scans/${id}?project_id=${projectId}`);
	},

	async cancel(id: string, projectId: string): Promise<ScanRead> {
		return api.post<ScanRead>(`/scans/${id}/cancel?project_id=${projectId}`);
	},

	async remove(id: string, projectId: string): Promise<void> {
		return api.delete<void>(`/scans/${id}?project_id=${projectId}`);
	},

	async activities(id: string, projectId: string): Promise<ScanActivityRead[]> {
		return api.get<ScanActivityRead[]>(`/scans/${id}/activities?project_id=${projectId}`);
	},

	async commands(id: string, projectId: string, activityId?: string): Promise<ScanCommandRead[]> {
		const sp = new URLSearchParams({ project_id: projectId });
		if (activityId) sp.append('activity_id', activityId);
		return api.get<ScanCommandRead[]>(`/scans/${id}/commands?${sp.toString()}`);
	},

	async command(id: string, commandId: string, projectId: string): Promise<ScanCommandDetail> {
		return api.get<ScanCommandDetail>(`/scans/${id}/commands/${commandId}?project_id=${projectId}`);
	}
};
