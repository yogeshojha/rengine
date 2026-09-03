import { TaskStatus } from './task-status';
import type { WhoisLookupType } from './whois';

export enum TargetType {
	DOMAIN = 'domain',
	IP = 'ip',
	IP_RANGE = 'ip_range',
	ASN = 'asn',
	URL = 'url'
}

export interface WhoisSummaryData {
	id: string;
	query_value: string;
	lookup_type: WhoisLookupType;
	name: string;
	registrant_name: string;
	registrar_name: string;
	country: string;
	network_cidr: string;
	registration_date: string | null;
	expiration_date: string | null;
	queried_at: string;
}

export interface DnsSummaryData {
	id: string;
	host: string;
	status_code: string;
	cdn: boolean;
	cdn_name: string;
	queried_at: string;
	record_counts: Record<string, number>;
}

export interface BgpSummaryData {
	// ASN targets
	prefix_count: number | null;
	peer_count: number | null;
	announced: boolean | null;

	// IP / IP_RANGE targets
	asn: number | null;
	prefix: string | null;
	holder: string | null;

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
	whois_status: TaskStatus;
	whois_error: string | null;
	whois_record_id: string | null;
	whois: WhoisSummaryData | null;
	bgp_status: TaskStatus;
	bgp: BgpSummaryData | null;
	dns_status: TaskStatus;
	dns_error: string | null;
	dns_lookup_id: string | null;
	dns: DnsSummaryData | null;
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

export interface EnrichmentRefreshResponse {
	target_id: string;
	enrichment_type: string;
	status: string;
	message: string;
}

export function getTargetTypeColor(_type: TargetType): string {
	return 'bg-muted/60 text-foreground/70 border-border/60';
}

export function formatTargetType(type: TargetType): string {
	return type.replace('_', ' ').toUpperCase();
}

export const TARGET_ASSET_NOUN: Record<TargetType, string> = {
	[TargetType.DOMAIN]: 'subdomain',
	[TargetType.IP]: 'host',
	[TargetType.IP_RANGE]: 'host',
	[TargetType.ASN]: 'host',
	[TargetType.URL]: 'host'
};

export function targetAssetNoun(type: string, count = 2): string {
	const noun = TARGET_ASSET_NOUN[type as TargetType] ?? 'host';
	return count === 1 ? noun : `${noun}s`;
}
