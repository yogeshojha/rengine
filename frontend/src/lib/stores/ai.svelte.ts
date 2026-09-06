import { aiApi } from '$lib/api/ai';
import type { AiCatalog, AiSettingsUpdate, AiStatus, AiTestResult } from '$lib/types/ai';
import { toast } from 'svelte-sonner';

function createAiStore() {
	let status = $state<AiStatus | null>(null);
	let catalog = $state<AiCatalog | null>(null);
	let isLoading = $state(false);
	let isSaving = $state(false);
	let hasFetched = $state(false);

	return {
		get status() {
			return status;
		},
		get catalog() {
			return catalog;
		},
		get isLoading() {
			return isLoading;
		},
		get isSaving() {
			return isSaving;
		},
		get hasFetched() {
			return hasFetched;
		},
		get available() {
			return Boolean(status?.enabled && status?.configured);
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			try {
				const [s, c] = await Promise.all([aiApi.status(), aiApi.catalog()]);
				status = s;
				catalog = c;
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'AI settings could not be loaded');
			} finally {
				isLoading = false;
			}
		},

		async save(body: AiSettingsUpdate): Promise<boolean> {
			isSaving = true;
			try {
				status = await aiApi.update(body);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'AI settings could not be saved');
				return false;
			} finally {
				isSaving = false;
			}
		},

		async test(body: Parameters<typeof aiApi.test>[0]): Promise<AiTestResult | null> {
			try {
				return await aiApi.test(body);
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'The test could not run');
				return null;
			}
		},

		async clearCache(): Promise<number> {
			try {
				const result = await aiApi.clearCache();
				if (status) status = { ...status, cached_narratives: 0 };
				return result.removed;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Cache could not be cleared');
				return 0;
			}
		},

		reset() {
			status = null;
			catalog = null;
			isLoading = false;
			isSaving = false;
			hasFetched = false;
		}
	};
}

export const ai = createAiStore();
