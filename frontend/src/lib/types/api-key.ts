// mirrors shared/enums/api_key.py:APIProvider
export enum APIProvider {
	VIEWDNS = 'viewdns',
	CHAOS = 'chaos',
	NETLAS = 'netlas',
	SECURITYTRAILS = 'securitytrails',
	HACKERONE = 'hackerone',
	INTIGRITI = 'intigriti',
	VULNX = 'vulnx',
	INTERACTSH = 'interactsh',
	GITHUB = 'github',
	TELEGRAM = 'telegram',
	VIRUSTOTAL = 'virustotal',
	CENSYS = 'censys',
	SHODAN = 'shodan',
	ALIENVAULT = 'alienvault',
	URLSCAN = 'urlscan',
	CERTSPOTTER = 'certspotter',
	FULLHUNT = 'fullhunt',
	LEAKIX = 'leakix',
	BEVIGIL = 'bevigil',
	INTELX = 'intelx',
	WHOISXMLAPI = 'whoisxmlapi',
	FOFA = 'fofa',
	ZOOMEYE = 'zoomeye'
}

export interface APIKeyRead {
	id: string;
	provider: APIProvider;
	key_value_masked: string;
	key_meta?: Record<string, unknown> | null;
	is_enabled: boolean;
	last_test_at: string | null;
	last_test_ok: boolean | null;
	last_test_message: string | null;
	created_at: string;
	updated_at: string;
}

export interface ProviderAccount {
	field: string;
	label: string;
	required: boolean;
	default: string | null;
}

export interface ProviderInfo {
	provider: APIProvider;
	name: string;
	description: string;
	docs_url: string;
	icon: string;
	account: ProviderAccount | null;
	setup: boolean;
	group: string;
	group_label: string;
	configured: boolean;
	is_enabled: boolean;
	testable: boolean;
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
