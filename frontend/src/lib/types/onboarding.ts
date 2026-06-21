export interface OnboardingSummary {
	proxies: number;
	channels: number;
	integrations: number;
	ai_enabled: boolean;
}

export interface OnboardingStatus {
	completed: boolean;
	can_setup: boolean;
	current_step: number;
	instance_name: string;
	mode: string;
	summary: OnboardingSummary;
}

export interface WizardData {
	mode: string | null;
	instanceName: string;
	twoFactorEnabled: boolean;
}

export interface StepFooter {
	onNext: () => void;
	nextLabel?: string;
	nextLoading?: boolean;
	nextDisabled?: boolean;
	canSkip?: boolean;
	hidden?: boolean;
}

export interface StepProps {
	data: WizardData;
	next: () => void;
	back: () => void;
	skip: () => void;
	isFirst: boolean;
	isLast: boolean;
	setFooter: (cfg: StepFooter) => void;
}
