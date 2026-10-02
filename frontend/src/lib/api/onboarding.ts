import { api } from './client';
import type { OnboardingStatus } from '$lib/types/onboarding';

export const onboardingApi = {
	getStatus: (): Promise<OnboardingStatus> => {
		return api.get<OnboardingStatus>('/onboarding/status');
	},

	saveProgress: (
		currentStep: number,
		state: Record<string, unknown>
	): Promise<OnboardingStatus> => {
		return api.patch<OnboardingStatus>('/onboarding/progress', {
			current_step: currentStep,
			state
		});
	},

	complete: (): Promise<OnboardingStatus> => {
		return api.post<OnboardingStatus>('/onboarding/complete');
	}
};
