import { DEFAULT_SCAN_CONTEXT, type ScanContextCreate } from '$lib/types/scan-context';
import type { ContextFormSection } from './context-form';
import { facetLine } from './context-summary';

interface ContextTemplate {
	key: string;
	title: string;
	focus: ContextFormSection;
	patch: Partial<ScanContextCreate>;
	facet?: string;
}

export const CONTEXT_TEMPLATES: readonly ContextTemplate[] = [
	{
		key: 'authenticated',
		title: 'Authenticated application',
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
		focus: 'scope',
		patch: {},
		facet: 'Included subdomains · excluded patterns, paths and IPs'
	},
	{
		key: 'gentle',
		title: 'Low impact',
		focus: 'rate',
		patch: { global_rate_limit_override: 20, thread_multiplier: 0.5, timeout_multiplier: 2.0 }
	},
	{
		key: 'blank',
		title: 'No overrides',
		focus: 'auth',
		patch: {}
	}
];

export function contextTemplate(key: string | null | undefined): ContextTemplate | undefined {
	return CONTEXT_TEMPLATES.find((t) => t.key === key);
}

export function templateDraft(key?: string | null): ScanContextCreate {
	const base = DEFAULT_SCAN_CONTEXT();
	const template = contextTemplate(key);
	return template ? { ...base, ...template.patch } : base;
}

export function templateFacet(template: ContextTemplate): string | null {
	if (template.facet) return template.facet;
	return Object.keys(template.patch).length ? facetLine(templateDraft(template.key)) : null;
}
