import { api } from './client';
import type {
	CveIntelRead,
	FindingIntel,
	IntelChange,
	SignalFinding,
	SyncResult,
	ThreatIntelStatus
} from '$lib/types/threat-intel';

export const threatIntelApi = {
	async status(projectId?: string): Promise<ThreatIntelStatus> {
		const qs = projectId ? `?project_id=${projectId}` : '';
		return api.get<ThreatIntelStatus>(`/threat-intel/status${qs}`);
	},

	async changes(projectId?: string, days = 7, limit = 50): Promise<IntelChange[]> {
		const params = new URLSearchParams({ days: String(days), limit: String(limit) });
		if (projectId) params.set('project_id', projectId);
		return api.get<IntelChange[]>(`/threat-intel/changes?${params}`);
	},

	async setAutoSync(enabled: boolean, projectId?: string): Promise<ThreatIntelStatus> {
		const qs = projectId ? `?project_id=${projectId}` : '';
		return api.put<ThreatIntelStatus>(`/threat-intel/auto-sync${qs}`, { enabled });
	},

	async sync(): Promise<SyncResult> {
		return api.post<SyncResult>('/threat-intel/sync', {});
	},

	async enrich(scanId: string): Promise<SyncResult> {
		return api.post<SyncResult>(`/threat-intel/scan/${scanId}/enrich`, {});
	},

	async signal(kind: string, projectId?: string, limit = 100): Promise<SignalFinding[]> {
		const params = new URLSearchParams({ limit: String(limit) });
		if (projectId) params.set('project_id', projectId);
		return api.get<SignalFinding[]>(`/threat-intel/signal/${kind}?${params}`);
	},

	async cve(cveId: string): Promise<CveIntelRead> {
		return api.get<CveIntelRead>(`/threat-intel/cve/${encodeURIComponent(cveId)}`);
	},

	async finding(vulnerabilityId: string): Promise<FindingIntel> {
		return api.get<FindingIntel>(`/threat-intel/finding/${vulnerabilityId}`);
	}
};
