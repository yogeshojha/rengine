export type WhoisLookupType = 'DOMAIN' | 'IP' | 'ASN';

export interface WhoisEntityAddress {
	po_box: string;
	ext_address: string;
	street_address: string;
	locality: string;
	region: string;
	postal_code: string;
	country: string;
}

export interface WhoisEntity {
	handle: string;
	name: string;
	email: string;
	tel: string;
	type: string;
	url: string;
	rir: string;
	whois_server: string;
	address: WhoisEntityAddress | null;
}

export interface WhoisParsedData {
	lookup_type: WhoisLookupType;
	query: string;
	handle: string;
	parent_handle: string;
	name: string;
	whois_server: string;
	object_class: string;
	terms_of_service_url: string;
	copyright_notice: string;
	description: string[];
	registration_date: string | null;
	last_changed_date: string | null;
	expiration_date: string | null;
	rir: string;
	url: string;
	entities: {
		registrant: WhoisEntity[];
		administrative: WhoisEntity[];
		technical: WhoisEntity[];
		abuse: WhoisEntity[];
		billing: WhoisEntity[];
		registrar: WhoisEntity[];
		sponsor: WhoisEntity[];
		noc: WhoisEntity[];
		routing: WhoisEntity[];
	};
	unicode_name: string;
	nameservers: string[];
	status: string[];
	dnssec: boolean;
}

export interface WhoisRecordRead {
	id: string;
	query_value: string;
	lookup_type: string;
	queried_at: string;
	handle: string;
	name: string;
	whois_server: string;
	object_class: string;
	rir: string;
	description: string;
	registration_date: string | null;
	last_changed_date: string | null;
	expiration_date: string | null;
	registrant_name: string;
	registrant_email: string;
	registrar_name: string;
	abuse_email: string;
	nameservers: string[] | null;
	domain_status: string[] | null;
	dnssec: boolean | null;
	country: string;
	ip_version: number | null;
	assignment_type: string;
	network_cidr: string;
	asn_range_start: number | null;
	asn_range_end: number | null;
	parsed_data: WhoisParsedData | null;
	created_at: string;
	updated_at: string;
}

export interface WhoisRecordSummary {
	id: string;
	query_value: string;
	lookup_type: string;
	name: string;
	registrant_name: string;
	registrar_name: string;
	country: string;
	network_cidr: string;
	registration_date: string | null;
	expiration_date: string | null;
	queried_at: string;
}

export interface WhoisCorrelationResult {
	correlation_type: string;
	correlation_value: string;
	records: WhoisRecordSummary[];
	count: number;
}

export interface WhoisRefreshResponse {
	record: WhoisRecordRead;
	previous_queried_at: string | null;
}

export interface WhoisLookupRequest {
	query: string;
	store_in_db?: boolean;
}

export interface WhoisLookupResponse {
	record: WhoisRecordRead | null;
	data: Record<string, unknown>;
	cached: boolean;
}

export type WhoisEntityRole =
	| 'registrant'
	| 'administrative'
	| 'technical'
	| 'abuse'
	| 'billing'
	| 'registrar'
	| 'sponsor'
	| 'noc'
	| 'routing';

export const ENTITY_ROLE_LABELS: Record<WhoisEntityRole, string> = {
	registrant: 'Registrant',
	administrative: 'Administrative',
	technical: 'Technical',
	abuse: 'Abuse',
	billing: 'Billing',
	registrar: 'Registrar',
	sponsor: 'Sponsor',
	noc: 'NOC',
	routing: 'Routing'
};

export const CORRELATION_TYPE_LABELS: Record<string, string> = {
	registrant: 'Shared Registrant',
	registrar: 'Shared Registrar',
	nameserver: 'Shared Nameserver',
	network: 'Same Network'
};

export function getStatusBadgeColor(status: string): string {
	const s = status.toLowerCase();
	if (s.includes('delete')) return 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20';
	if (s.includes('transfer'))
		return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
	if (s.includes('update'))
		return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
	if (s.includes('renew'))
		return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
	if (s.includes('hold'))
		return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
	return 'bg-muted text-muted-foreground border-border';
}

export function getCorrelationIcon(type: string): string {
	switch (type) {
		case 'registrant':
			return 'UserRound';
		case 'registrar':
			return 'Building';
		case 'nameserver':
			return 'Server';
		case 'network':
			return 'Network';
		default:
			return 'Link';
	}
}
