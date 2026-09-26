// mirrors shared/definitions/secrets.py
import type { BadgeVariant } from '$lib/components/ui/badge';

export enum SecretState {
	EXPOSED = 'exposed',
	PUBLIC = 'public',
	EXPIRED = 'expired'
}

export const STATE_ORDER: SecretState[] = [
	SecretState.EXPOSED,
	SecretState.PUBLIC,
	SecretState.EXPIRED
];

export const STATE_LABELS: Record<SecretState, string> = {
	[SecretState.EXPOSED]: 'Exposed',
	[SecretState.PUBLIC]: 'Public',
	[SecretState.EXPIRED]: 'Expired'
};

export const STATE_BADGE: Record<SecretState, BadgeVariant> = {
	[SecretState.EXPOSED]: 'warning',
	[SecretState.PUBLIC]: 'outline',
	[SecretState.EXPIRED]: 'info'
};

export enum SecretGroup {
	CLOUD = 'cloud',
	CODE = 'code',
	PAYMENTS = 'payments',
	MESSAGING = 'messaging',
	AI = 'ai',
	AUTH = 'auth',
	DATA = 'data',
	PLATFORM = 'platform',
	CONTACT = 'contact'
}

export const GROUP_ORDER: SecretGroup[] = [
	SecretGroup.CLOUD,
	SecretGroup.CODE,
	SecretGroup.PAYMENTS,
	SecretGroup.MESSAGING,
	SecretGroup.AI,
	SecretGroup.AUTH,
	SecretGroup.DATA,
	SecretGroup.PLATFORM,
	SecretGroup.CONTACT
];

export const GROUP_LABELS: Record<SecretGroup, string> = {
	[SecretGroup.CLOUD]: 'Cloud',
	[SecretGroup.CODE]: 'Source control and packages',
	[SecretGroup.PAYMENTS]: 'Payments',
	[SecretGroup.MESSAGING]: 'Messaging',
	[SecretGroup.AI]: 'AI providers',
	[SecretGroup.AUTH]: 'Authentication',
	[SecretGroup.DATA]: 'Data stores',
	[SecretGroup.PLATFORM]: 'Platform and tooling',
	[SecretGroup.CONTACT]: 'Contacts'
};

export enum SecretSource {
	BODY = 'body',
	HEADER = 'header',
	ENDPOINT_BODY = 'endpoint_body',
	ENDPOINT_HEADER = 'endpoint_header',
	FINDING = 'finding'
}

export const SOURCE_LABELS: Record<SecretSource, string> = {
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
	too_long: 'Over the length cap'
};

export const STATE_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	...STATE_ORDER.map((key) => ({ key, label: STATE_LABELS[key] }))
];
