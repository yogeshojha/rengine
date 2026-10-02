// mirrors shared/definitions/secrets.py
import type { BadgeVariant } from '$lib/components/ui/badge';

export enum SecretState {
	EXPOSED = 'exposed',
	PUBLIC = 'public',
	EXPIRED = 'expired'
}

export const STATE_ORDER: string[] = [SecretState.EXPOSED, SecretState.PUBLIC, SecretState.EXPIRED];

export const STATE_LABELS: Record<string, string> = {
	[SecretState.EXPOSED]: 'Exposed',
	[SecretState.PUBLIC]: 'Public',
	[SecretState.EXPIRED]: 'Expired'
};

export const STATE_BADGE: Record<string, BadgeVariant> = {
	[SecretState.EXPOSED]: 'warning',
	[SecretState.PUBLIC]: 'outline',
	[SecretState.EXPIRED]: 'info'
};

export enum SecretSource {
	BODY = 'body',
	HEADER = 'header',
	ENDPOINT_BODY = 'endpoint_body',
	ENDPOINT_HEADER = 'endpoint_header',
	FINDING = 'finding'
}

export const SOURCE_LABELS: Record<string, string> = {
	[SecretSource.BODY]: 'Web asset body',
	[SecretSource.HEADER]: 'Web asset headers',
	[SecretSource.ENDPOINT_BODY]: 'Endpoint body',
	[SecretSource.ENDPOINT_HEADER]: 'Endpoint headers',
	[SecretSource.FINDING]: 'Finding response'
};

export const DROP_REASON_LABELS: Record<string, string> = {
	placeholder: 'Placeholder value',
	low_entropy: 'Low entropy',
	overlap: 'Inside a longer match',
	file_name: 'File name, not an address',
	example_domain: 'Example domain',
	hex_local_part: 'Hex local part',
	undecodable: 'Token did not decode',
	template: 'Template expression',
	too_long: 'Over the length cap',
	link_scheme: 'Link scheme, not a user'
};

export const STATE_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	...STATE_ORDER.map((key) => ({ key, label: STATE_LABELS[key] }))
];
