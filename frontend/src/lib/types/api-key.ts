export enum APIProvider {
	VIEWDNS = 'viewdns',
	CHAOS = 'chaos',
	NETLAS = 'netlas',
	SECURITYTRAILS = 'securitytrails',
	HACKERONE = 'hackerone'
}

export interface ProviderMeta {
	name: string;
	description: string;
	docs_url: string;
	color: string;
	icon: string;
	requires_username: boolean;
}

export interface APIKeyRead {
	id: string;
	provider: APIProvider;
	key_value_masked: string;
	key_meta?: Record<string, unknown> | null;
	is_enabled: boolean;
	usage_counter: number;
	last_used_at: string | null;
	created_at: string;
	updated_at: string;
	meta: ProviderMeta;
}

export interface ProviderInfo {
	provider: APIProvider;
	name: string;
	description: string;
	docs_url: string;
	color: string;
	icon: string;
	requires_username: boolean;
	configured: boolean;
	is_enabled: boolean;
}

export interface APIKeyCreate {
	provider: APIProvider;
	key_value: string;
	key_meta?: Record<string, unknown> | null;
}

export interface APIKeyUpdate {
	key_value?: string;
	is_enabled?: boolean;
	key_meta?: Record<string, unknown> | null;
}
