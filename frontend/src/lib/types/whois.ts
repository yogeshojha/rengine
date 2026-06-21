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
