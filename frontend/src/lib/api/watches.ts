import {
	WatchHostFilter,
	type StreamStatus,
	type Watch,
	type WatchCreate,
	type WatchEvent,
	type WatchHost,
	type WatchHostCounts,
	type WatchPreview,
	type WatchUpdate
} from '$lib/types/watch';
import type { PaginatedResponse } from '$lib/types/pagination';
import { api, toQuery } from './client';

const BASE = '/bounty-programs/watches';

export const watchesApi = {
	list(projectId: string): Promise<Watch[]> {
		return api.get<Watch[]>(`${BASE}${toQuery({ project_id: projectId })}`);
	},

	get(id: string, projectId: string): Promise<Watch> {
		return api.get<Watch>(`${BASE}/${id}${toQuery({ project_id: projectId })}`);
	},

	preview(platform: string, handle: string, projectId: string): Promise<WatchPreview> {
		return api.get<WatchPreview>(
			`/bounty-programs/${platform}/${encodeURIComponent(handle)}/watch/preview${toQuery({
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
		return api.patch<Watch>(`${BASE}/${id}${toQuery({ project_id: projectId })}`, patch);
	},

	remove(id: string, projectId: string): Promise<unknown> {
		return api.delete(`${BASE}/${id}${toQuery({ project_id: projectId })}`);
	},

	markSeen(id: string, projectId: string): Promise<{ seen_at: string }> {
		return api.post<{ seen_at: string }>(
			`${BASE}/${id}/seen${toQuery({ project_id: projectId })}`,
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
	): Promise<PaginatedResponse<WatchHost>> {
		return api.get<PaginatedResponse<WatchHost>>(
			`${BASE}/${id}/hosts${toQuery({
				project_id: projectId,
				state: options.state === WatchHostFilter.All ? null : options.state,
				since: options.since,
				q: options.q,
				page: options.page,
				size: options.size
			})}`
		);
	},

	hostCounts(id: string, projectId: string, since?: string | null): Promise<WatchHostCounts> {
		return api.get<WatchHostCounts>(
			`${BASE}/${id}/hosts/counts${toQuery({ project_id: projectId, since })}`
		);
	},

	muteHost(id: string, hostId: string, projectId: string): Promise<WatchHost> {
		return api.post<WatchHost>(
			`${BASE}/${id}/hosts/${hostId}/mute${toQuery({ project_id: projectId })}`,
			{}
		);
	},

	events(
		id: string,
		projectId: string,
		options: { page: number; size: number; kind?: string | null; since?: string | null }
	): Promise<PaginatedResponse<WatchEvent>> {
		return api.get<PaginatedResponse<WatchEvent>>(
			`${BASE}/${id}/events${toQuery({
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
