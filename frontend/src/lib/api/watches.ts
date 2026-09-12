import type {
	StreamStatus,
	Watch,
	WatchCreate,
	WatchEvent,
	WatchHost,
	WatchHostCounts,
	WatchHostFilter,
	WatchPreview,
	WatchUpdate
} from '$lib/types/watch';
import { api } from './client';
import type { Paged } from './bounty-programs';

function query(params: Record<string, unknown>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		search.set(key, String(value));
	}
	const qs = search.toString();
	return qs ? `?${qs}` : '';
}

const BASE = '/bounty-programs/watches';

export const watchesApi = {
	list(projectId: string): Promise<Watch[]> {
		return api.get<Watch[]>(`${BASE}${query({ project_id: projectId })}`);
	},

	get(id: string, projectId: string): Promise<Watch> {
		return api.get<Watch>(`${BASE}/${id}${query({ project_id: projectId })}`);
	},

	preview(platform: string, handle: string, projectId: string): Promise<WatchPreview> {
		return api.get<WatchPreview>(
			`/bounty-programs/${platform}/${encodeURIComponent(handle)}/watch/preview${query({
				project_id: projectId
			})}`
		);
	},

	create(platform: string, handle: string, body: WatchCreate): Promise<Watch> {
		return api.post<Watch>(
			`/bounty-programs/${platform}/${encodeURIComponent(handle)}/watch`,
			body
		);
	},

	update(id: string, projectId: string, patch: WatchUpdate): Promise<Watch> {
		return api.patch<Watch>(`${BASE}/${id}${query({ project_id: projectId })}`, patch);
	},

	remove(id: string, projectId: string): Promise<unknown> {
		return api.delete(`${BASE}/${id}${query({ project_id: projectId })}`);
	},

	markSeen(id: string, projectId: string): Promise<{ seen_at: string }> {
		return api.post<{ seen_at: string }>(
			`${BASE}/${id}/seen${query({ project_id: projectId })}`,
			{}
		);
	},

	reconcile(id: string, projectId: string): Promise<Record<string, number>> {
		return api.post<Record<string, number>>(
			`${BASE}/${id}/reconcile${query({ project_id: projectId })}`,
			{}
		);
	},

	hosts(
		id: string,
		projectId: string,
		options: {
			state?: WatchHostFilter | null;
			since?: string | null;
			q?: string | null;
			page: number;
			size: number;
		}
	): Promise<Paged<WatchHost>> {
		return api.get<Paged<WatchHost>>(
			`${BASE}/${id}/hosts${query({
				project_id: projectId,
				state: options.state === 'all' ? null : options.state,
				since: options.since,
				q: options.q,
				page: options.page,
				size: options.size
			})}`
		);
	},

	hostCounts(id: string, projectId: string, since?: string | null): Promise<WatchHostCounts> {
		return api.get<WatchHostCounts>(
			`${BASE}/${id}/hosts/counts${query({ project_id: projectId, since })}`
		);
	},

	muteHost(id: string, hostId: string, projectId: string): Promise<WatchHost> {
		return api.post<WatchHost>(
			`${BASE}/${id}/hosts/${hostId}/mute${query({ project_id: projectId })}`,
			{}
		);
	},

	events(
		id: string,
		projectId: string,
		options: { page: number; size: number; kind?: string | null; since?: string | null }
	): Promise<Paged<WatchEvent>> {
		return api.get<Paged<WatchEvent>>(
			`${BASE}/${id}/events${query({
				project_id: projectId,
				page: options.page,
				size: options.size,
				kind: options.kind,
				since: options.since
			})}`
		);
	},

	stream(): Promise<StreamStatus> {
		return api.get<StreamStatus>(`${BASE}/stream`);
	},

	validateQuery(text: string): Promise<{ error: string | null }> {
		return api.post<{ error: string | null }>(`${BASE}/validate-query`, { query: text });
	}
};
