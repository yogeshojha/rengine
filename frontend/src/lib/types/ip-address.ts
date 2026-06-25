export interface IpAddressRead {
	id: string;
	scan_id: string;
	target_id: string;
	ip: string;
	version: number;
	source: string;
	ptr_hostnames: string[];
	asn: number | null;
	asn_org: string | null;
	prefix: string | null;
	country: string | null;
	is_cdn: boolean;
	cdn_name: string | null;
	is_alive: boolean | null;
	discovered_at: string;
}

export interface IpAddressSummary {
	total: number;
	alive: number;
	cdn: number;
	by_source: Record<string, number>;
}
