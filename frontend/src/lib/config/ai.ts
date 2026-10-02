export const AIProvider = {
	OPENAI: 'openai',
	ANTHROPIC: 'anthropic',
	AZURE_OPENAI: 'azure_openai',
	GOOGLE: 'google'
} as const;
export type AIProviderValue = (typeof AIProvider)[keyof typeof AIProvider];

export const DEFAULT_AI_PROVIDER: AIProviderValue = AIProvider.OPENAI;

export interface AIProviderMeta {
	value: AIProviderValue;
	name: string;
	model: string;
}

export const AI_PROVIDERS: readonly AIProviderMeta[] = [
	{ value: AIProvider.OPENAI, name: 'OpenAI', model: 'gpt-6-sol' },
	{ value: AIProvider.ANTHROPIC, name: 'Anthropic', model: 'claude-opus-5-5' },
	{ value: AIProvider.AZURE_OPENAI, name: 'Azure OpenAI', model: 'gpt-6-sol' },
	{ value: AIProvider.GOOGLE, name: 'Google', model: 'gemini-3.8-flash' }
] as const;

export interface AIFeature {
	key: string;
	label: string;
	hint: string;
}

export const AI_FEATURES: readonly AIFeature[] = [
	{
		key: 'vuln_descriptions',
		label: 'Vulnerability descriptions',
		hint: 'Plain-language summaries of findings'
	},
	{
		key: 'impact_assessment',
		label: 'Impact assessment',
		hint: 'Severity and business-impact reasoning'
	},
	{ key: 'remediation', label: 'Remediation guidance', hint: 'Suggested fixes per finding' },
	{ key: 'auto_report', label: 'Automated reports', hint: 'Draft scan reports automatically' }
] as const;
