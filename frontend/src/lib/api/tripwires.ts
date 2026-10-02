import type { PaginatedResponse } from '$lib/types/pagination';
import type {
	Tripwire,
	TripwireBacktest,
	TripwireCatalog,
	TripwireCreate,
	TripwirePreview,
	TripwirePreviewRequest,
	TripwireRun,
	TripwireRunCounts,
	TripwireUpdate
} from '$lib/types/tripwire';
import { api, toQuery } from './client';

const BASE = '/tripwires';

export const tripwiresApi = {
	list(projectId: string): Promise<Tripwire[]> {
		return api.get<Tripwire[]>(`${BASE}${toQuery({ project_id: projectId })}`);
	},

	create(projectId: string, body: TripwireCreate): Promise<Tripwire> {
		return api.post<Tripwire>(`${BASE}${toQuery({ project_id: projectId })}`, body);
	},

	update(id: string, projectId: string, body: TripwireUpdate): Promise<Tripwire> {
		return api.patch<Tripwire>(`${BASE}/${id}${toQuery({ project_id: projectId })}`, body);
	},

	remove(id: string, projectId: string): Promise<void> {
		return api.delete<void>(`${BASE}/${id}${toQuery({ project_id: projectId })}`);
	},

	catalog(): Promise<TripwireCatalog> {
		return api.get<TripwireCatalog>(`${BASE}/catalog`);
	},

	preview(projectId: string, body: TripwirePreviewRequest): Promise<TripwirePreview> {
		return api.post<TripwirePreview>(`${BASE}/preview${toQuery({ project_id: projectId })}`, body);
	},

	backtest(projectId: string, body: TripwirePreviewRequest): Promise<TripwireBacktest> {
		return api.post<TripwireBacktest>(
			`${BASE}/backtest${toQuery({ project_id: projectId })}`,
			body
		);
	},

	run(runId: string, projectId: string): Promise<TripwireRun> {
		return api.get<TripwireRun>(`${BASE}/runs/${runId}${toQuery({ project_id: projectId })}`);
	},

	runs(
		id: string,
		projectId: string,
		params: { status?: string | null; page?: number; size?: number } = {}
	): Promise<PaginatedResponse<TripwireRun>> {
		return api.get<PaginatedResponse<TripwireRun>>(
			`${BASE}/${id}/runs${toQuery({ project_id: projectId, ...params })}`
		);
	},

	runCounts(id: string, projectId: string): Promise<TripwireRunCounts> {
		return api.get<TripwireRunCounts>(
			`${BASE}/${id}/runs/counts${toQuery({ project_id: projectId })}`
		);
	}
};
