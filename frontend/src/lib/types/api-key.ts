export enum APIProvider {
	VIEWDNS = 'viewdns'
}

export interface ProviderMeta {
	name: string;
	description: string;
	docs_url: string;
	color: string;
	icon: string;
}

export interface APIKeyRead {
	id: string;
	provider: APIProvider;
	key_value_masked: string;
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
	configured: boolean;
	is_enabled: boolean;
}

export interface APIKeyCreate {
	provider: APIProvider;
	key_value: string;
}

export interface APIKeyUpdate {
	key_value?: string;
	is_enabled?: boolean;
}
