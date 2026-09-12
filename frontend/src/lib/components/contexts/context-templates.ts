import { DEFAULT_SCAN_CONTEXT, type ScanContextCreate } from '$lib/types/scan-context';
import type { ContextFormSection } from './context-form';

export interface ContextTemplate {
	key: string;
	title: string;
	description: string;
	focus: ContextFormSection;
	patch: Partial<ScanContextCreate>;
}

export const CONTEXT_TEMPLATES: readonly ContextTemplate[] = [
	{
		key: 'authenticated',
		title: 'Authenticated application',
		description: 'Sends a bearer token with every request and restricts scanning to HTTPS.',
		focus: 'auth',
		patch: {
			auth_type: 'bearer',
			auth: { ...DEFAULT_SCAN_CONTEXT().auth, auth_type: 'bearer' },
			http_protocol: 'https_only'
		}
	},
	{
		key: 'scoped',
		title: 'Program scope',
		description: 'Excludes out-of-scope subdomains, paths and IP ranges.',
		focus: 'scope',
		patch: {}
	},
	{
		key: 'gentle',
		title: 'Low impact',
		description: 'Caps the request rate at 20/s, halves threads and doubles timeouts.',
		focus: 'rate',
		patch: { global_rate_limit_override: 20, thread_multiplier: 0.5, timeout_multiplier: 2.0 }
	},
	{
		key: 'blank',
		title: 'No overrides',
		description: 'No credentials or overrides.',
		focus: 'auth',
		patch: {}
	}
] as const;

export function contextTemplate(key: string | null | undefined): ContextTemplate | undefined {
	return CONTEXT_TEMPLATES.find((t) => t.key === key);
}

export function templateDraft(key?: string | null): ScanContextCreate {
	const base = DEFAULT_SCAN_CONTEXT();
	const template = contextTemplate(key);
	return template ? { ...base, ...template.patch } : base;
}
