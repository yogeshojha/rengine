import { api } from './client';
import type { OnboardingStatus } from '$lib/types/onboarding';
import type { Project } from '$lib/types/project';

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
	},

	createFirstProject: (data: {
		name: string;
		description?: string | null;
		label?: string | null;
	}): Promise<Project> => {
		return api.post<Project>('/onboarding/first-project', data);
	}
};
