import { api } from './client';
import type {
	InterestCatalog,
	InterestDismissal,
	InterestFilter,
	InterestPage,
	InterestRule,
	InterestRuleCreate,
	InterestRuleUpdate,
	RulePreview,
	RuleSuggestion
} from '$lib/types/interest';

export const interestApi = {
	catalog(): Promise<InterestCatalog> {
		return api.get<InterestCatalog>('/interest/catalog');
	},

	rules(projectId: string): Promise<InterestRule[]> {
		return api.get<InterestRule[]>(`/interest/rules?project_id=${projectId}`);
	},

	createRule(projectId: string, body: InterestRuleCreate): Promise<InterestRule> {
		return api.post<InterestRule>(`/interest/rules?project_id=${projectId}`, body);
	},

	updateRule(projectId: string, id: string, body: InterestRuleUpdate): Promise<InterestRule> {
		return api.patch<InterestRule>(`/interest/rules/${id}?project_id=${projectId}`, body);
	},

	deleteRule(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/interest/rules/${id}?project_id=${projectId}`);
	},

	preview(query: string, scanId?: string): Promise<RulePreview> {
		const suffix = scanId ? `?scan_id=${scanId}` : '';
		return api.post<RulePreview>(`/interest/rules/preview${suffix}`, { query });
	},

	scan(scanId: string, filter: InterestFilter): Promise<InterestPage> {
		return api.post<InterestPage>(`/interest/scan/${scanId}`, filter);
	},

	suggestions(scanId: string): Promise<RuleSuggestion[]> {
		return api.get<RuleSuggestion[]>(`/interest/scan/${scanId}/suggestions`);
	},

	judge(scanId: string): Promise<{ status: string }> {
		return api.post<{ status: string }>(`/interest/scan/${scanId}/judge`, {});
	},

	dismiss(body: {
		host: string;
		target_id: string;
		kind?: string;
		note?: string | null;
	}): Promise<void> {
		return api.post<void>('/interest/dismiss', body);
	},

	dismissals(projectId: string): Promise<InterestDismissal[]> {
		return api.get<InterestDismissal[]>(`/interest/dismissals?project_id=${projectId}`);
	},

	dismissalsForTarget(targetId: string): Promise<InterestDismissal[]> {
		return api.get<InterestDismissal[]>(`/interest/dismissals?target_id=${targetId}`);
	},

	restore(id: string): Promise<void> {
		return api.delete<void>(`/interest/dismissals/${id}`);
	}
};
