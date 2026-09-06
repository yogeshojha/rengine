import { instanceSettingsApi } from '$lib/api/instanceSettings';
import type { InstanceSettings, InstanceSettingsUpdate } from '$lib/types/instance-settings';
import { toast } from 'svelte-sonner';

function createInstanceSettingsStore() {
	let settings = $state<InstanceSettings | null>(null);
	let isLoading = $state(false);
	let hasFetched = $state(false);

	return {
		get settings() {
			return settings;
		},
		get isLoading() {
			return isLoading;
		},
		get hasFetched() {
			return hasFetched;
		},

		async fetch() {
			if (isLoading) return;
			isLoading = true;
			try {
				settings = await instanceSettingsApi.get();
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Instance settings could not be loaded');
			} finally {
				isLoading = false;
			}
		},

		async update(data: InstanceSettingsUpdate): Promise<InstanceSettings | null> {
			try {
				settings = await instanceSettingsApi.update(data);
				return settings;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Instance settings could not be updated');
				return null;
			}
		},

		async testAi(data: {
			provider: string;
			model?: string;
			api_key?: string;
		}): Promise<{ success: boolean; message: string } | null> {
			try {
				return await instanceSettingsApi.testAi(data);
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'AI connection test failed');
				return null;
			}
		},

		clear() {
			settings = null;
			hasFetched = false;
		}
	};
}

export const instanceSettingsStore = createInstanceSettingsStore();
