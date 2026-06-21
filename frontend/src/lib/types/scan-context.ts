export const AUTH_TYPES = ['none', 'header', 'bearer', 'basic', 'cookie', 'api_key'] as const;
export const HTTP_PROTOCOLS = ['both', 'http_only', 'https_only'] as const;
export const VALID_RATE_TOOLS = ['naabu', 'ffuf', 'nuclei'] as const;
export const MULTIPLIERS = [0.5, 1.0, 2.0] as const;

export type AuthType = (typeof AUTH_TYPES)[number];
export type HttpProtocol = (typeof HTTP_PROTOCOLS)[number];

export { MASK } from '$lib/constants';

export interface AuthHeader {
	name: string;
	value: string;
}

export interface AuthConfig {
	auth_type: string;
	bearer_token: string | null;
	basic_username: string | null;
	basic_password: string | null;
	header_name: string | null;
	header_value: string | null;
	cookie_value: string | null;
	api_key_name: string | null;
	api_key_value: string | null;
}

export interface ScanContextRead {
	id: string;
	project_id: string;
	created_by: string;
	name: string;
	description: string | null;
	auth_type: AuthType;
	auth: AuthConfig;
	auth_summary: string;
	extra_headers: AuthHeader[];
	global_rate_limit_override: number | null;
	per_tool_rate_overrides: Record<string, number>;
	thread_multiplier: number;
	timeout_multiplier: number;
	excluded_subdomains: string[];
	excluded_paths: string[];
	excluded_ips: string[];
	included_subdomains: string[];
	follow_redirects_override: boolean | null;
	http_protocol: HttpProtocol;
	proxy_id: string | null;
	compare_baseline_scan_id: string | null;
	scan_only_new_assets: boolean;
	created_at: string;
	updated_at: string;
	last_used_at: string | null;
	last_used_scan_id: string | null;
}

export type ScanContextCreate = Omit<
	ScanContextRead,
	| 'id'
	| 'project_id'
	| 'created_by'
	| 'auth_summary'
	| 'created_at'
	| 'updated_at'
	| 'last_used_at'
	| 'last_used_scan_id'
> & {
	auth?: Partial<AuthConfig>;
};

export type ScanContextUpdate = Partial<ScanContextCreate>;

export function defaultAuthConfig(): AuthConfig {
	return {
		auth_type: 'none',
		bearer_token: null,
		basic_username: null,
		basic_password: null,
		header_name: null,
		header_value: null,
		cookie_value: null,
		api_key_name: null,
		api_key_value: null
	};
}

export function DEFAULT_SCAN_CONTEXT(): ScanContextCreate {
	return {
		name: '',
		description: null,
		auth_type: 'none',
		auth: defaultAuthConfig(),
		extra_headers: [],
		global_rate_limit_override: null,
		per_tool_rate_overrides: {},
		thread_multiplier: 1.0,
		timeout_multiplier: 1.0,
		excluded_subdomains: [],
		excluded_paths: [],
		excluded_ips: [],
		included_subdomains: [],
		follow_redirects_override: null,
		http_protocol: 'both',
		proxy_id: null,
		compare_baseline_scan_id: null,
		scan_only_new_assets: false
	};
}
