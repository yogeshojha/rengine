import type { TaskStatus } from './task-status';
import type {
	TargetType,
	OrganizationSummary,
	TagSummary,
	BgpSummaryData,
	DnsSummaryData
} from './target';
import type { WhoisRecordRead } from './whois';
import type {
	AnnouncedPrefixRead,
	ASNNeighbourRead,
	ASOverviewRead,
	NetworkInfoRead,
	PrefixOverviewRead,
	RelatedPrefixRead
} from './ripestat';

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

export interface DnsLookupRead extends DnsSummaryData {
	records: DnsRecordRead[];
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
	summary: BgpSummaryData | null;
	as_overview: ASOverviewRead | null;
	announced_prefixes: AnnouncedPrefixRead[];
	neighbours: ASNNeighbourRead[];
	network_info: NetworkInfoRead[];
	prefix_overview: PrefixOverviewRead[];
	related_prefixes: RelatedPrefixRead[];
	abuse_contacts: AbuseContactDetail[];
}

export interface TargetDnsDetailResponse {
	target_id: string;
	target_type: TargetType;
	status: TaskStatus;
	error: string | null;
	lookup: DnsLookupRead | null;
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
