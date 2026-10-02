import { api } from './client';
import type {
	AiCallPage,
	AiCatalog,
	AiConnection,
	AiConnectionCreate,
	AiConnectionUpdate,
	AiModelList,
	AiModelsRequest,
	AiOnboarding,
	AiOnboardingRead,
	AiSettingsUpdate,
	AiStatus,
	AiTestRequest,
	AiTestResult
} from '$lib/types/ai';

export const aiApi = {
	calls(limit: number, before?: string): Promise<AiCallPage> {
		const query = new URLSearchParams({ limit: String(limit) });
		if (before) query.set('before', before);
		return api.get<AiCallPage>(`/ai/calls?${query}`);
	},

	status(): Promise<AiStatus> {
		return api.get<AiStatus>('/ai/status');
	},

	catalog(): Promise<AiCatalog> {
		return api.get<AiCatalog>('/ai/catalog');
	},

	update(body: AiSettingsUpdate): Promise<AiStatus> {
		return api.patch<AiStatus>('/ai/settings', body);
	},

	connections(): Promise<AiConnection[]> {
		return api.get<AiConnection[]>('/ai/connections');
	},

	createConnection(body: AiConnectionCreate): Promise<AiConnection> {
		return api.post<AiConnection>('/ai/connections', body);
	},

	updateConnection(id: string, body: AiConnectionUpdate): Promise<AiConnection> {
		return api.patch<AiConnection>(`/ai/connections/${id}`, body);
	},

	deleteConnection(id: string): Promise<void> {
		return api.delete<void>(`/ai/connections/${id}`);
	},

	useConnection(id: string): Promise<AiConnection> {
		return api.post<AiConnection>(`/ai/connections/${id}/use`);
	},

	testConnection(id: string): Promise<AiTestResult> {
		return api.post<AiTestResult>(`/ai/connections/${id}/test`);
	},

	models(body: AiModelsRequest): Promise<AiModelList> {
		return api.post<AiModelList>('/ai/models', body);
	},

	test(body: AiTestRequest): Promise<AiTestResult> {
		return api.post<AiTestResult>('/ai/test', body);
	},

	clearCache(): Promise<{ removed: number }> {
		return api.delete<{ removed: number }>('/ai/cache');
	},

	onboarding(): Promise<AiOnboardingRead> {
		return api.get<AiOnboardingRead>('/onboarding/ai');
	},

	saveOnboarding(body: AiOnboarding): Promise<AiOnboardingRead> {
		return api.put<AiOnboardingRead>('/onboarding/ai', body);
	}
};
