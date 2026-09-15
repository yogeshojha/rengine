// mirrors shared/definitions/estate.py
import { RELATION_LABELS } from './relations';

export enum EstateReason {
	REDIRECT = 'redirect',
	CNAME = 'cname',
	CERT_SUBJECT = 'cert_subject',
	CERT_SAN = 'cert_san',
	ADDRESS = 'address'
}

export enum EstateStrength {
	DIRECT = 'direct',
	SHARED = 'shared'
}

export enum ProviderKind {
	EDGE = 'edge',
	HOSTING = 'hosting',
	DNS = 'dns',
	MAIL = 'mail'
}

export const ESTATE_REASON_LABELS: Record<string, string> = {
	[EstateReason.REDIRECT]: 'Redirects to',
	[EstateReason.CNAME]: 'Delegates to',
	[EstateReason.CERT_SUBJECT]: 'Serves a certificate for',
	[EstateReason.CERT_SAN]: 'Named on a certificate',
	[EstateReason.ADDRESS]: 'Same address',
	...RELATION_LABELS
};

export const ESTATE_REASON_ORDER: string[] = [
	EstateReason.REDIRECT,
	EstateReason.CNAME,
	EstateReason.CERT_SUBJECT,
	EstateReason.CERT_SAN,
	...Object.keys(RELATION_LABELS),
	EstateReason.ADDRESS
];

export const ESTATE_REASON_FILL: Record<string, string> = {
	[EstateReason.REDIRECT]: 'var(--chart-3)',
	[EstateReason.CNAME]: 'var(--chart-1)',
	[EstateReason.CERT_SUBJECT]: 'var(--chart-4)',
	[EstateReason.CERT_SAN]: 'var(--chart-4)',
	[EstateReason.ADDRESS]: 'var(--chart-5)'
};

export const ESTATE_STRENGTH_LABELS: Record<string, string> = {
	[EstateStrength.DIRECT]: 'Direct',
	[EstateStrength.SHARED]: 'Shared'
};

export const PROVIDER_KIND_LABELS: Record<string, string> = {
	[ProviderKind.EDGE]: 'edge',
	[ProviderKind.HOSTING]: 'hosting',
	[ProviderKind.DNS]: 'nameservers',
	[ProviderKind.MAIL]: 'mail'
};

export const NEIGHBOUR_MAX_NAMES = 5;
