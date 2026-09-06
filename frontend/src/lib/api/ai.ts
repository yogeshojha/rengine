import { api } from './client';
import type { AiCatalog, AiSettingsUpdate, AiStatus, AiTestResult, AiUsage } from '$lib/types/ai';

export const aiApi = {
	status(): Promise<AiStatus> {
		return api.get<AiStatus>('/ai/status');
	},

	catalog(): Promise<AiCatalog> {
		return api.get<AiCatalog>('/ai/catalog');
	},

	usage(): Promise<AiUsage> {
		return api.get<AiUsage>('/ai/usage');
	},

	update(body: AiSettingsUpdate): Promise<AiStatus> {
		return api.patch<AiStatus>('/ai/settings', body);
	},

	test(body: {
		provider?: string;
		model?: string;
		api_key?: string;
		workspace_id?: string;
	}): Promise<AiTestResult> {
		return api.post<AiTestResult>('/ai/test', body);
	},

	clearCache(): Promise<{ removed: number }> {
		return api.delete<{ removed: number }>('/ai/cache');
	}
};
