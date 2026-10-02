import { api } from './client';
import type {
	ScanActivityRead,
	ScanBatchCreate,
	ScanCancelAll,
	ScanCommandDetail,
	ScanCommandRead,
	ScanCreate,
	ScanDaily,
	ScanPreview,
	ScanRead,
	ScanSortDir,
	ScanSortKey,
	ScanStats,
	ScanStatus,
	ScanTargetTrend
} from '$lib/types/scan';
import type { PaginatedResponse } from '$lib/types/pagination';
import type {
	FocusedRun,
	Recheck,
	RescanCreate,
	RescanSchema,
	RunPreview
} from '$lib/types/recheck';

interface ScanFilterParams {
	target_id?: string | string[];
	status?: ScanStatus[];
	engine?: string[];
	search?: string;
	sort_by?: ScanSortKey;
	sort_dir?: ScanSortDir;
	include_focused?: boolean;
	severity?: string[];
	short?: boolean | null;
	added?: boolean | null;
	started_from?: string | null;
	started_to?: string | null;
	latest?: boolean;
}

interface ListScansParams extends ScanFilterParams {
	page?: number;
	size?: number;
}

function buildScanQuery(projectId: string, params: ScanFilterParams): URLSearchParams {
	const sp = new URLSearchParams({ project_id: projectId });
	for (const id of [params.target_id ?? []].flat()) sp.append('target_id', id);
	for (const s of params.status ?? []) sp.append('status', s);
	for (const e of params.engine ?? []) sp.append('engine', e);
	if (params.search?.trim()) sp.append('search', params.search.trim());
	if (params.sort_by) sp.append('sort_by', params.sort_by);
	if (params.sort_dir) sp.append('sort_dir', params.sort_dir);
	if (params.include_focused) sp.append('include_focused', 'true');
	for (const v of params.severity ?? []) sp.append('severity', v);
	if (params.short != null) sp.append('short', String(params.short));
	if (params.added != null) sp.append('added', String(params.added));
	if (params.started_from) sp.append('started_from', params.started_from);
	if (params.started_to) sp.append('started_to', params.started_to);
	if (params.latest) sp.append('latest', 'true');
	return sp;
}

export const scansApi = {
	async rescanSchema(): Promise<RescanSchema> {
		return api.get<RescanSchema>('/scans/rescan/schema');
	},

	async rescan(projectId: string, body: RescanCreate): Promise<FocusedRun> {
		return api.post<FocusedRun>(`/scans/rescan?project_id=${projectId}`, body);
	},

	async rescanPreview(projectId: string, body: RescanCreate): Promise<RunPreview> {
		return api.post<RunPreview>(`/scans/rescan/preview?project_id=${projectId}`, body);
	},

	async rechecks(projectId: string, scanId: string): Promise<Recheck[]> {
		return api.get<Recheck[]>(`/scans/${scanId}/rechecks?project_id=${projectId}`);
	},

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

	async stats(
		projectId: string,
		targetIds: string[] = [],
		includeFocused = false
	): Promise<ScanStats> {
		const sp = new URLSearchParams({ project_id: projectId });
		for (const id of targetIds) sp.append('target_id', id);
		if (includeFocused) sp.append('include_focused', 'true');
		return api.get<ScanStats>(`/scans/stats?${sp.toString()}`);
	},

	async latest(projectId: string, targetIds: string[]): Promise<ScanRead[]> {
		const sp = new URLSearchParams({ project_id: projectId });
		for (const id of targetIds) sp.append('target_id', id);
		return api.get<ScanRead[]>(`/scans/latest?${sp}`);
	},

	async trends(projectId: string, targetIds: string[]): Promise<ScanTargetTrend[]> {
		const sp = new URLSearchParams({ project_id: projectId });
		for (const id of targetIds) sp.append('target_id', id);
		return api.get<ScanTargetTrend[]>(`/scans/trends?${sp}`);
	},

	async daily(projectId: string, days: number, targetIds: string[] = []): Promise<ScanDaily> {
		const sp = new URLSearchParams({ project_id: projectId, days: String(days) });
		for (const id of targetIds) sp.append('target_id', id);
		return api.get<ScanDaily>(`/scans/daily?${sp}`);
	},

	async get(id: string, projectId: string): Promise<ScanRead> {
		return api.get<ScanRead>(`/scans/${id}?project_id=${projectId}`);
	},

	async cancel(id: string, projectId: string): Promise<ScanRead> {
		return api.post<ScanRead>(`/scans/${id}/cancel?project_id=${projectId}`);
	},

	async cancelAll(projectId: string, targetIds: string[] = []): Promise<ScanCancelAll> {
		const sp = new URLSearchParams({ project_id: projectId });
		for (const id of targetIds) sp.append('target_id', id);
		return api.post<ScanCancelAll>(`/scans/cancel-all?${sp.toString()}`);
	},

	async pause(id: string, projectId: string): Promise<ScanRead> {
		return api.post<ScanRead>(`/scans/${id}/pause?project_id=${projectId}`);
	},

	async resume(id: string, projectId: string): Promise<ScanRead> {
		return api.post<ScanRead>(`/scans/${id}/resume?project_id=${projectId}`);
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
