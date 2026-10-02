export const AIProvider = {
	OPENAI: 'openai',
	ANTHROPIC: 'anthropic',
	GOOGLE: 'google',
	OPENAI_COMPATIBLE: 'openai_compatible'
} as const;

export const DEFAULT_AI_PROVIDER = AIProvider.ANTHROPIC;
