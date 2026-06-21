export const PROXY_SCHEMES = ['http', 'https', 'socks5'] as const;
export const PROXY_MODES = ['single', 'rotating'] as const;

export interface ProxyEndpoint {
	scheme: string;
	host: string;
	port: number;
	username?: string | null;
	password?: string | null;
}

export interface ProxyEndpointRead {
	scheme: string;
	host: string;
	port: number;
	username: string | null;
	has_password: boolean;
	url_masked: string;
}

export interface ProxyRead {
	id: string;
	name: string;
	description: string | null;
	mode: string;
	is_active: boolean;
	is_default: boolean;
	endpoints: ProxyEndpointRead[];
	endpoint_count: number;
	created_at: string;
	updated_at: string;
	last_test_at: string | null;
	last_test_ok: boolean | null;
	last_test_message: string | null;
}

export interface ProxyCreate {
	name: string;
	description?: string | null;
	mode?: string;
	is_active?: boolean;
	is_default?: boolean;
	endpoints: ProxyEndpoint[];
}

export interface ProxyUpdate {
	name?: string;
	description?: string | null;
	mode?: string;
	is_active?: boolean;
	is_default?: boolean;
	endpoints?: ProxyEndpoint[] | null;
}

export interface ProxyTestResult {
	success: boolean;
	message: string;
	latency_ms: number | null;
}
