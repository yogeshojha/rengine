import type { MatchEvidence, QueryError } from './asset-query';
import type { CrossLink } from './crosslink';

export interface SubdomainRead {
	target_value?: string | null;
	id: string;
	scan_id: string;
	target_id: string;
	name: string;
	sources: string[];
	resolved_ips: string[];
	cname: string | null;
	is_active: boolean;
	is_wildcard: boolean;
	is_excluded: boolean;
	is_important: boolean;
	http_url: string | null;
	final_url: string | null;
	http_status: number | null;
	page_title: string | null;
	content_type: string | null;
	content_length: number | null;
	response_time: number | null;
	webserver: string | null;
	tech: string[];
	is_cdn: boolean;
	cdn_name: string | null;
	waf: string | null;
	asn: number | null;
	asn_org: string | null;
	favicon_hash: string | null;
	tls_not_after: string | null;
	tls_expired: boolean | null;
	tls_self_signed: boolean | null;
	screenshot_path: string | null;
	hygiene_issues: string[];
	hygiene_checked: string[];
	ports?: number[];
	endpoint_count?: number;
	title_count?: number;
	title_targets?: number;
	favicon_count?: number;
	favicon_targets?: number;
	render_hash?: string | null;
	render_count?: number;
	render_targets?: number;
	vuln_count?: number;
	vuln_severity?: string | null;
	vuln_kev?: boolean;
	matched_in?: MatchEvidence[];
	cross_links?: CrossLink[];
	discovered_at: string;
}

export interface RenderGroup {
	hash: string;
	label: string | null;
	count: number;
	hosts: string[];
	screenshot_path: string | null;
	query: string;
}

export interface RenderGroups {
	groups: RenderGroup[];
	total_groups: number;
	grouped: number;
	ungrouped: number;
	blank: number;
	unrendered: number;
	error?: QueryError | null;
}

export interface SubdomainSummary {
	total: number;
	active: number;
	sources: Record<string, number>;
}

export interface TargetSubdomainRead {
	name: string;
	sources: string[];
	resolved_ips: string[];
	cname: string | null;
	is_active: boolean;
	is_wildcard: boolean;
	is_excluded: boolean;
	scan_count: number;
	last_scan_id: string;
	first_seen: string;
	last_seen: string;
}
