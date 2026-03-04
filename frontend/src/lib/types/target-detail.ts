import type { TaskStatus } from './task-status';
import type { TargetType, OrganizationSummary, TagSummary } from './target';
import type { WhoisRecordRead } from './whois';

export interface DnsRecordRead {
	id: string;
	record_type: string;
	value: string;
	priority: number | null;
	weight: number | null;
	port: number | null;
	soa_email: string | null;
	soa_serial: number | null;
	caa_tag: string | null;
	caa_flag: number | null;
}

export interface DnsLookupRead {
	id: string;
	host: string;
	status_code: string;
	cdn: boolean;
	cdn_name: string;
	queried_at: string;
	record_counts: Record<string, number>;
	records: DnsRecordRead[];
}

export interface AnnouncedPrefixDetail {
	prefix: string;
	ip_version: number;
	first_seen: string | null;
	last_seen: string | null;
}

export interface ASNNeighbourDetail {
	neighbour_asn: number;
	relationship: string;
	power: number;
}

export interface ASOverviewDetail {
	asn: number;
	holder: string;
	rir: string | null;
	announced: boolean;
	block_name: string | null;
	block_resource: string | null;
}

export interface NetworkInfoDetail {
	ip: string;
	prefix: string;
	asn: number;
}

export interface PrefixOverviewDetail {
	prefix: string;
	asn: number;
	holder: string;
	is_announced: boolean;
}

export interface RelatedPrefixDetail {
	related_prefix: string;
	relationship: string;
	origin_asn: number | null;
}

export interface AbuseContactDetail {
	resource: string;
	abuse_email: string;
	rir: string | null;
}

export interface TargetBgpDetailResponse {
	target_id: string;
	target_type: TargetType;
	status: TaskStatus;
	summary: unknown;
	as_overview: ASOverviewDetail | null;
	announced_prefixes: AnnouncedPrefixDetail[];
	neighbours: ASNNeighbourDetail[];
	network_info: NetworkInfoDetail[];
	prefix_overview: PrefixOverviewDetail[];
	related_prefixes: RelatedPrefixDetail[];
	abuse_contacts: AbuseContactDetail[];
}

export interface TargetDetailRead {
	id: string;
	target_value: string;
	display_name: string | null;
	target_type: TargetType;
	project_id: string;
	created_at: string;
	updated_at: string;
	created_by: string;
	organizations: OrganizationSummary[];
	tags: TagSummary[];

	whois_status: TaskStatus;
	whois_error: string | null;
	whois: WhoisRecordRead | null;

	dns_status: TaskStatus;
	dns_error: string | null;
	dns: DnsLookupRead | null;

	bgp_status: TaskStatus;
	bgp: TargetBgpDetailResponse | null;
}
