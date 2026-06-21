import { api } from './client';
import type { InstanceSettings, InstanceSettingsUpdate } from '$lib/types/instance-settings';

export const instanceSettingsApi = {
	get: (): Promise<InstanceSettings> => {
		return api.get<InstanceSettings>('/instance-settings');
	},

	update: (data: InstanceSettingsUpdate): Promise<InstanceSettings> => {
		return api.patch<InstanceSettings>('/instance-settings', data);
	},

	testAi: (data: {
		provider: string;
		model?: string;
		api_key?: string;
	}): Promise<{ success: boolean; message: string }> => {
		return api.post<{ success: boolean; message: string }>('/instance-settings/ai/test', data);
	}
};
