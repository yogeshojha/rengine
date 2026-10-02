import { MASK } from '$lib/constants';
import type { AuthConfig, AuthType, ScanContextCreate } from '$lib/types/scan-context';
import type { SvelteSet } from 'svelte/reactivity';

export type ContextFormSection = 'identity' | 'auth' | 'rate' | 'scope' | 'runtime' | 'proxy';

const AUTH_SECRET_FIELD = {
	bearer: 'bearer_token',
	basic: 'basic_password',
	header: 'header_value',
	cookie: 'cookie_value',
	api_key: 'api_key_value'
} as const satisfies Partial<Record<AuthType, keyof AuthConfig>>;

export type SecretField = (typeof AUTH_SECRET_FIELD)[keyof typeof AUTH_SECRET_FIELD];

const SECRET_KEYS: SecretField[] = Object.values(AUTH_SECRET_FIELD);

export function secretFieldFor(type: AuthType): SecretField | undefined {
	return (AUTH_SECRET_FIELD as Partial<Record<AuthType, SecretField>>)[type];
}

const PATTERN_METACHARS = /[*?^$()[\]{}+|\\]/;

export function patternError(v: string): string | null {
	if (v.includes('.') && !PATTERN_METACHARS.test(v)) {
		return 'Domain names are not patterns. Enter a keyword, wildcard or regex';
	}
	return null;
}

export function pathError(v: string): string | null {
	return v.startsWith('/') ? null : 'Path must start with /';
}

export function ipError(v: string): string | null {
	const cidr = v.split('/');
	if (cidr.length > 2) return 'Enter a valid IP or CIDR';
	const ip = cidr[0];
	const v4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
	const v6 = /^[0-9a-fA-F:]+$/;
	const isV4 = v4.test(ip) && ip.split('.').every((o) => Number(o) <= 255);
	const isV6 = v6.test(ip) && ip.includes(':');
	if (!isV4 && !isV6) return 'Enter a valid IP or CIDR';
	if (cidr.length === 2) {
		const n = Number(cidr[1]);
		const maxPrefix = isV6 ? 128 : 32;
		if (cidr[1].trim() === '' || !Number.isInteger(n) || n < 0 || n > maxPrefix) {
			return 'Invalid CIDR prefix';
		}
	}
	return null;
}

export function validateDraft(
	draft: ScanContextCreate
): { message: string; section: ContextFormSection } | null {
	if (!draft.name.trim()) return { message: 'Name is required', section: 'identity' };
	const badPatterns = draft.excluded_subdomains.filter((v) => patternError(v) !== null).length;
	if (badPatterns > 0)
		return {
			message: `${badPatterns} invalid pattern${badPatterns === 1 ? '' : 's'} in Scope`,
			section: 'scope'
		};
	const badPaths = draft.excluded_paths.filter((p) => pathError(p) !== null).length;
	if (badPaths > 0)
		return {
			message: `${badPaths} invalid path${badPaths === 1 ? '' : 's'} in Scope`,
			section: 'scope'
		};
	const badIps = draft.excluded_ips.filter((ip) => ipError(ip) !== null).length;
	if (badIps > 0)
		return { message: `${badIps} invalid IP${badIps === 1 ? '' : 's'} in Scope`, section: 'scope' };
	const badHeader = draft.extra_headers.some((h) => !h.name.trim() && h.value.trim());
	if (badHeader) return { message: 'A header in Authentication has no name', section: 'auth' };
	if (draft.auth_type === 'api_key' && !draft.auth?.api_key_name?.trim())
		return { message: 'API key authentication requires a key name', section: 'auth' };
	return null;
}

export function markTouchedSecrets(auth: AuthConfig, touched: SvelteSet<string>): void {
	for (const k of SECRET_KEYS) {
		const v = auth[k];
		if (v != null && v !== MASK) touched.add(k);
	}
}

function buildAuthPayload(
	draft: ScanContextCreate,
	touched: SvelteSet<string>
): Partial<AuthConfig> | undefined {
	const a = draft.auth;
	if (!a) return undefined;
	const out: Partial<AuthConfig> = { auth_type: a.auth_type };

	const visible: (keyof AuthConfig)[] = ['basic_username', 'header_name', 'api_key_name'];
	for (const k of visible) {
		if (a[k] != null) out[k] = a[k];
	}

	for (const k of SECRET_KEYS) {
		const v = a[k];
		if (touched.has(k) && v !== MASK) out[k] = v;
	}
	return out;
}

export function buildContextPayload(
	draft: ScanContextCreate,
	touched: SvelteSet<string>,
	withProxy: boolean
): ScanContextCreate {
	const payload: ScanContextCreate = {
		name: draft.name,
		description: draft.description,
		auth_type: draft.auth_type,
		auth: buildAuthPayload(draft, touched) as ScanContextCreate['auth'],
		extra_headers: draft.extra_headers,
		global_rate_limit_override: draft.global_rate_limit_override,
		per_tool_rate_overrides: draft.per_tool_rate_overrides,
		thread_multiplier: draft.thread_multiplier,
		timeout_multiplier: draft.timeout_multiplier,
		excluded_subdomains: draft.excluded_subdomains,
		excluded_paths: draft.excluded_paths,
		excluded_ips: draft.excluded_ips,
		included_subdomains: draft.included_subdomains,
		follow_redirects_override: draft.follow_redirects_override,
		http_protocol: draft.http_protocol
	};
	if (withProxy) payload.proxy_id = draft.proxy_id;
	return payload;
}
