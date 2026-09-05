export const ASSET_STATES = ['all', 'current', 'new', 'gone'] as const;
export type AssetState = (typeof ASSET_STATES)[number];

export const ASSET_SORTS = [
	{ key: 'name', label: 'Host' },
	{ key: 'status', label: 'HTTP status' },
	{ key: 'first_seen', label: 'First seen' },
	{ key: 'last_seen', label: 'Last seen' },
	{ key: 'scans', label: 'Scans seen in' }
] as const;
export type AssetSort = (typeof ASSET_SORTS)[number]['key'];

export interface TargetAssetRow {
	name: string;
	is_active: boolean;
	is_wildcard: boolean;
	resolved_ips: string[];
	cname: string | null;
	sources: string[];
	scan_count: number;
	first_seen: string;
	last_seen: string;
	last_scan_id: string;
	current: boolean;
	is_new: boolean;
	status_code: number | null;
	title: string | null;
	webserver: string | null;
	tech: string[];
	ip: string | null;
	asn_org: string | null;
	is_cdn: boolean;
	cdn_name: string | null;
	screenshot_path: string | null;
}

export interface TargetAssetFilter {
	search?: string | null;
	state?: AssetState;
	live?: boolean;
	sort?: AssetSort;
	order?: 'asc' | 'desc';
	limit?: number;
	offset?: number;
}

export interface TargetAssetFacets {
	total: number;
	current: number;
	new: number;
	gone: number;
	live: number;
	baseline: boolean;
	latest_scan_id: string | null;
}

export interface TargetAssetPage {
	items: TargetAssetRow[];
	total: number;
	facets: TargetAssetFacets;
}
