import { api } from './client';
import { appendTargetScope, type TargetScope } from '$lib/utilities/surface-scope';
import type {
	FindingIntel,
	IntelChange,
	SignalFinding,
	SyncResult,
	ThreatIntelStatus
} from '$lib/types/threat-intel';

export const threatIntelApi = {
	async status(projectId?: string, scope: TargetScope = {}): Promise<ThreatIntelStatus> {
		const params = appendTargetScope(new URLSearchParams(), scope);
		if (projectId) params.set('project_id', projectId);
		const qs = params.size ? `?${params}` : '';
		return api.get<ThreatIntelStatus>(`/threat-intel/status${qs}`);
	},

	async changes(
		projectId?: string,
		days = 7,
		limit = 50,
		scope: TargetScope = {}
	): Promise<IntelChange[]> {
		const params = new URLSearchParams({ days: String(days), limit: String(limit) });
		if (projectId) params.set('project_id', projectId);
		appendTargetScope(params, scope);
		return api.get<IntelChange[]>(`/threat-intel/changes?${params}`);
	},

	async setAutoSync(enabled: boolean, projectId?: string): Promise<ThreatIntelStatus> {
		const qs = projectId ? `?project_id=${projectId}` : '';
		return api.put<ThreatIntelStatus>(`/threat-intel/auto-sync${qs}`, { enabled });
	},

	async sync(): Promise<SyncResult> {
		return api.post<SyncResult>('/threat-intel/sync', {});
	},

	async signal(
		kind: string,
		projectId?: string,
		limit = 100,
		scope: TargetScope = {}
	): Promise<SignalFinding[]> {
		const params = appendTargetScope(new URLSearchParams({ limit: String(limit) }), scope);
		if (projectId) params.set('project_id', projectId);
		return api.get<SignalFinding[]>(`/threat-intel/signal/${kind}?${params}`);
	},

	async finding(vulnerabilityId: string): Promise<FindingIntel> {
		return api.get<FindingIntel>(`/threat-intel/finding/${vulnerabilityId}`);
	}
};
