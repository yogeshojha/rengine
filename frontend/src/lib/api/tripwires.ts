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
import { api } from './client';

function query(params: Record<string, unknown>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		search.set(key, String(value));
	}
	const qs = search.toString();
	return qs ? `?${qs}` : '';
}

const BASE = '/tripwires';

export const tripwiresApi = {
	list(projectId: string): Promise<Tripwire[]> {
		return api.get<Tripwire[]>(`${BASE}${query({ project_id: projectId })}`);
	},

	get(id: string, projectId: string): Promise<Tripwire> {
		return api.get<Tripwire>(`${BASE}/${id}${query({ project_id: projectId })}`);
	},

	create(projectId: string, body: TripwireCreate): Promise<Tripwire> {
		return api.post<Tripwire>(`${BASE}${query({ project_id: projectId })}`, body);
	},

	update(id: string, projectId: string, body: TripwireUpdate): Promise<Tripwire> {
		return api.patch<Tripwire>(`${BASE}/${id}${query({ project_id: projectId })}`, body);
	},

	remove(id: string, projectId: string): Promise<void> {
		return api.delete<void>(`${BASE}/${id}${query({ project_id: projectId })}`);
	},

	catalog(): Promise<TripwireCatalog> {
		return api.get<TripwireCatalog>(`${BASE}/catalog`);
	},

	preview(projectId: string, body: TripwirePreviewRequest): Promise<TripwirePreview> {
		return api.post<TripwirePreview>(`${BASE}/preview${query({ project_id: projectId })}`, body);
	},

	backtest(projectId: string, body: TripwirePreviewRequest): Promise<TripwireBacktest> {
		return api.post<TripwireBacktest>(`${BASE}/backtest${query({ project_id: projectId })}`, body);
	},

	run(runId: string, projectId: string): Promise<TripwireRun> {
		return api.get<TripwireRun>(`${BASE}/runs/${runId}${query({ project_id: projectId })}`);
	},

	runs(
		id: string,
		projectId: string,
		params: { status?: string | null; page?: number; size?: number } = {}
	): Promise<PaginatedResponse<TripwireRun>> {
		return api.get<PaginatedResponse<TripwireRun>>(
			`${BASE}/${id}/runs${query({ project_id: projectId, ...params })}`
		);
	},

	runCounts(id: string, projectId: string): Promise<TripwireRunCounts> {
		return api.get<TripwireRunCounts>(
			`${BASE}/${id}/runs/counts${query({ project_id: projectId })}`
		);
	}
};
