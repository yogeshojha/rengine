import { api } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
import type { EndpointFilter } from '$lib/utilities/endpoints';
import type {
	Candidate,
	CandidatePage,
	Connector,
	ConnectorCoverage,
	ConnectorCreate,
	ConnectorCreated,
	ConnectorSession,
	ConnectorSpec,
	DiscoveredDomain,
	TargetAdded,
	ConnectorUpdate
} from '$lib/types/connector';
import type { ScanRead } from '$lib/types/scan';

export const connectorsApi = {
	catalog(): Promise<ConnectorSpec[]> {
		return api.get<ConnectorSpec[]>('/connectors/catalog');
	},

	list(projectId: string): Promise<Connector[]> {
		return api.get<Connector[]>(`/connectors?project_id=${projectId}`);
	},

	create(body: ConnectorCreate): Promise<ConnectorCreated> {
		return api.post<ConnectorCreated>('/connectors', body);
	},

	update(id: string, projectId: string, body: ConnectorUpdate): Promise<Connector> {
		return api.patch<Connector>(`/connectors/${id}?project_id=${projectId}`, body);
	},

	rotate(id: string, projectId: string): Promise<ConnectorCreated> {
		return api.post<ConnectorCreated>(`/connectors/${id}/rotate?project_id=${projectId}`);
	},

	remove(id: string, projectId: string): Promise<void> {
		return api.delete<void>(`/connectors/${id}?project_id=${projectId}`);
	},

	candidates(
		id: string,
		projectId: string,
		params: { state?: string; host?: string; notice?: string; search?: string; page?: number } = {}
	): Promise<CandidatePage> {
		const query = new URLSearchParams({ project_id: projectId });
		for (const [key, value] of Object.entries(params)) {
			if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
		}
		return api.get<CandidatePage>(`/connectors/${id}/candidates?${query.toString()}`);
	},

	setState(
		id: string,
		projectId: string,
		ids: string[],
		state: Candidate['state']
	): Promise<{ changed: number }> {
		return api.post<{ changed: number }>(
			`/connectors/${id}/candidates/state?project_id=${projectId}`,
			{ ids, state }
		);
	},

	clear(id: string, projectId: string): Promise<{ removed: number }> {
		return api.delete<{ removed: number }>(`/connectors/${id}/candidates?project_id=${projectId}`);
	},

	sendEndpoints(
		id: string,
		projectId: string,
		scanId: string,
		body: { endpoint_ids?: string[]; filter?: EndpointFilter; limit?: number }
	): Promise<{ queued: number }> {
		return api.post<{ queued: number }>(
			`/connectors/${id}/send-endpoints?${scopeQuery({ projectId, scanId })}`,
			body
		);
	},

	send(id: string, projectId: string, ids: string[]): Promise<{ queued: number }> {
		return api.post<{ queued: number }>(`/connectors/${id}/send?project_id=${projectId}`, {
			ids,
			kind: 'repeater'
		});
	},

	scan(id: string, projectId: string, ids: string[] = []): Promise<ScanRead> {
		return api.post<ScanRead>(`/connectors/${id}/scan?project_id=${projectId}`, { ids });
	},

	discovered(id: string, projectId: string): Promise<DiscoveredDomain[]> {
		return api.get<DiscoveredDomain[]>(`/connectors/${id}/discovered?project_id=${projectId}`);
	},

	addTarget(id: string, projectId: string, domain: string, scan = false): Promise<TargetAdded> {
		return api.post<TargetAdded>(`/connectors/${id}/discovered/add?project_id=${projectId}`, {
			domain,
			scan
		});
	},

	dismissDomain(id: string, projectId: string, domain: string): Promise<{ dismissed: number }> {
		return api.post<{ dismissed: number }>(
			`/connectors/${id}/discovered/dismiss?project_id=${projectId}`,
			{ domain }
		);
	},

	coverage(id: string, projectId: string): Promise<ConnectorCoverage[]> {
		return api.get<ConnectorCoverage[]>(`/connectors/${id}/coverage?project_id=${projectId}`);
	},

	sessions(id: string, projectId: string): Promise<ConnectorSession[]> {
		return api.get<ConnectorSession[]>(`/connectors/${id}/sessions?project_id=${projectId}`);
	}
};
