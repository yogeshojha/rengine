import { MASK, type ScanContextCreate, type AuthConfig } from '$lib/types/scan-context';
import type { SvelteSet } from 'svelte/reactivity';

export type ContextFormSection = 'identity' | 'auth' | 'rate' | 'scope' | 'runtime' | 'proxy';

const SECRET_KEYS = [
	'bearer_token',
	'basic_password',
	'header_value',
	'cookie_value',
	'api_key_value'
] as const;

function isPathValid(v: string): boolean {
	return v.startsWith('/');
}

function isIpValid(v: string): boolean {
	const cidr = v.split('/');
	if (cidr.length > 2) return false;
	const ip = cidr[0];
	const v4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
	const v6 = /^[0-9a-fA-F:]+$/;
	const isV4 = v4.test(ip) && ip.split('.').every((o) => Number(o) <= 255);
	const isV6 = v6.test(ip) && ip.includes(':');
	if (!isV4 && !isV6) return false;
	if (cidr.length === 2) {
		const n = Number(cidr[1]);
		const maxPrefix = isV6 ? 128 : 32;
		if (cidr[1].trim() === '' || !Number.isInteger(n) || n < 0 || n > maxPrefix) return false;
	}
	return true;
}

export function validateDraft(
	draft: ScanContextCreate
): { message: string; section: ContextFormSection } | null {
	if (!draft.name.trim()) return { message: 'Name is required', section: 'identity' };
	const badPaths = draft.excluded_paths.filter((p) => !isPathValid(p)).length;
	if (badPaths > 0) return { message: `Fix ${badPaths} invalid path in Scope`, section: 'scope' };
	const badIps = draft.excluded_ips.filter((ip) => !isIpValid(ip)).length;
	if (badIps > 0) return { message: `Fix ${badIps} invalid IP in Scope`, section: 'scope' };
	const badHeader = draft.extra_headers.some((h) => !h.name.trim() && h.value.trim());
	if (badHeader)
		return { message: 'A header has a value but no name in Authentication', section: 'auth' };
	if (draft.auth_type === 'api_key' && !draft.auth?.api_key_name?.trim())
		return { message: 'API key auth needs a key name in Authentication', section: 'auth' };
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
	touched: SvelteSet<string>
): ScanContextCreate {
	return {
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
		http_protocol: draft.http_protocol,
		proxy_id: draft.proxy_id,
		compare_baseline_scan_id: null,
		scan_only_new_assets: false
	};
}
