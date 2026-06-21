import { onboardingApi } from '$lib/api/onboarding';
import type { OnboardingStatus } from '$lib/types/onboarding';
import { toast } from 'svelte-sonner';

function createOnboardingStore() {
	let status = $state<OnboardingStatus | null>(null);
	let isLoading = $state(false);
	let hasFetched = $state(false);

	return {
		get status() {
			return status;
		},
		get isLoading() {
			return isLoading;
		},
		get hasFetched() {
			return hasFetched;
		},
		get completed() {
			return status?.completed ?? false;
		},
		get canSetup() {
			return status?.can_setup ?? false;
		},

		async fetchStatus() {
			if (hasFetched || isLoading) return;
			isLoading = true;
			try {
				status = await onboardingApi.getStatus();
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to load onboarding status');
			} finally {
				isLoading = false;
			}
		},

		async refresh() {
			isLoading = true;
			try {
				status = await onboardingApi.getStatus();
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to load onboarding status');
			} finally {
				isLoading = false;
			}
		},

		clear() {
			status = null;
			hasFetched = false;
		}
	};
}

export const onboardingStore = createOnboardingStore();
