export enum TargetType {
	DOMAIN = 'domain',
	IP = 'ip',
	IP_RANGE = 'ip_range',
	ASN = 'asn',
	URL = 'url'
}

export enum WhoisStatus {
	PENDING = 'pending',
	QUERYING = 'querying',
	SUCCESS = 'success',
	FAILED = 'failed',
	NOT_APPLICABLE = 'not_applicable'
}

export interface WhoisSummaryData {
	id: string;
	query_value: string;
	lookup_type: 'DOMAIN' | 'IP' | 'ASN';
	name: string;
	registrant_name: string;
	registrar_name: string;
	country: string;
	network_cidr: string;
	registration_date: string | null;
	expiration_date: string | null;
	queried_at: string;
}

export interface OrganizationSummary {
	id: string;
	name: string;
	slug: string;
}

export interface TagSummary {
	id: string;
	name: string;
	slug: string;
	color: string;
}

export interface TargetBase {
	target_value: string;
	display_name?: string | null;
}

export interface Target extends TargetBase {
	id: string;
	target_type: TargetType;
	project_id: string;
	created_at: string;
	updated_at: string;
	created_by: string;
	whois_status: WhoisStatus;
	whois_error: string | null;
	whois_record_id: string | null;
	whois: WhoisSummaryData | null;
	organizations: OrganizationSummary[];
	tags: TagSummary[];
}

export interface TargetCreate extends TargetBase {
	project_slug: string;
	organization_names?: string[];
	tag_names?: string[];
}

export interface TargetUpdate {
	display_name?: string | null;
	organization_names?: string[] | null;
	tag_names?: string[] | null;
}

export interface TargetValidationRequest {
	target_value: string;
}

export interface TargetValidationResponse {
	valid: boolean;
	target_type: TargetType | null;
	error: string | null;
	target_value: string;
}

export interface TargetBulkCreateRequest {
	project_slug: string;
	targets: string[];
	organization_names?: string[];
	tag_names?: string[];
}

export interface TargetImportItem {
	target_value: string;
	tags?: string[];
	organizations?: string[];
	display_name?: string | null;
}

export interface TargetImportRequest {
	project_slug: string;
	targets: TargetImportItem[];
}

export interface TargetImportResult {
	target_value: string;
	success: boolean;
	target_type: TargetType | null;
	target_id: string | null;
	error: string | null;
}

export interface TargetBulkCreateResponse {
	total: number;
	imported: number;
	failed: number;
	skipped_duplicates: number;
	results: TargetImportResult[];
}

export interface TargetPreviewItem {
	target_value: string;
	target_type?: TargetType | null;
	tags?: string[];
	organizations?: string[];
	display_name?: string | null;
	error?: string;
}

export function getTargetTypeColor(type: TargetType): string {
	switch (type) {
		case TargetType.DOMAIN:
			return 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20';
		case TargetType.IP:
			return 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20';
		case TargetType.IP_RANGE:
			return 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20';
		case TargetType.ASN:
			return 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20';
		case TargetType.URL:
			return 'bg-pink-500/10 text-pink-700 dark:text-pink-400 border-pink-500/20';
		default:
			return 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20';
	}
}

export function formatTargetType(type: TargetType): string {
	return type.replace('_', ' ').toUpperCase();
}
