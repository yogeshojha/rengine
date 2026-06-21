export interface AnnouncedPrefixRead {
	prefix: string;
	ip_version: number;
	first_seen: string | null;
	last_seen: string | null;
}

export interface ASNNeighbourRead {
	neighbour_asn: number;
	relationship: string; // 'upstream' | 'downstream' | 'uncertain'
	power: number;
}

export interface ASOverviewRead {
	asn: number;
	holder: string;
	rir: string | null;
	announced: boolean;
	block_name: string | null;
	block_resource: string | null;
}

export interface NetworkInfoRead {
	ip: string;
	prefix: string;
	asn: number;
}

export interface AbuseContactRead {
	resource: string;
	abuse_emails: string[];
	rir: string | null;
}

export interface PrefixOverviewRead {
	prefix: string;
	asn: number;
	holder: string;
	is_announced: boolean;
}

export interface RelatedPrefixRead {
	related_prefix: string;
	relationship: string; // 'overlap' | 'more_specific' | 'less_specific'
	origin_asn: number | null;
}
