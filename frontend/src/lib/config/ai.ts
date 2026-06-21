export const AIProvider = {
	OPENAI: 'openai',
	ANTHROPIC: 'anthropic',
	AZURE_OPENAI: 'azure_openai',
	GOOGLE: 'google'
} as const;
export type AIProviderValue = (typeof AIProvider)[keyof typeof AIProvider];

export interface AIProviderMeta {
	value: AIProviderValue;
	name: string;
	model: string;
}

export const AI_PROVIDERS: readonly AIProviderMeta[] = [
	{ value: AIProvider.OPENAI, name: 'OpenAI', model: 'gpt-4o-mini' },
	{ value: AIProvider.ANTHROPIC, name: 'Anthropic', model: 'claude-3-5-haiku-latest' },
	{ value: AIProvider.AZURE_OPENAI, name: 'Azure OpenAI', model: 'gpt-4o-mini' },
	{ value: AIProvider.GOOGLE, name: 'Google', model: 'gemini-1.5-flash' }
] as const;

export interface AIFeature {
	key: string;
	label: string;
	hint: string;
}

export const AI_FEATURES: readonly AIFeature[] = [
	{ key: 'vuln_descriptions', label: 'Vulnerability descriptions', hint: 'Plain-language summaries of findings' },
	{ key: 'impact_assessment', label: 'Impact assessment', hint: 'Severity and business-impact reasoning' },
	{ key: 'remediation', label: 'Remediation guidance', hint: 'Suggested fixes per finding' },
	{ key: 'auto_report', label: 'Automated reports', hint: 'Draft scan reports automatically' }
] as const;
