import { api } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
import type { DomainPostureSummary } from '$lib/types/domain-posture';

export const domainPostureApi = {
	async scan(projectId: string, scanId: string): Promise<DomainPostureSummary> {
		return api.get<DomainPostureSummary>(`/domain-posture?${scopeQuery({ projectId, scanId })}`);
	},

	async project(projectId: string): Promise<DomainPostureSummary> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.get<DomainPostureSummary>(`/domain-posture/project?${sp.toString()}`);
	},

	async target(projectId: string, targetId: string): Promise<DomainPostureSummary> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.get<DomainPostureSummary>(`/domain-posture/target/${targetId}?${sp.toString()}`);
	}
};
