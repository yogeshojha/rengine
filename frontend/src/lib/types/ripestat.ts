export const PEER_RELATIONSHIPS = ['upstream', 'downstream', 'uncertain'] as const;
export type PeerRelationship = (typeof PEER_RELATIONSHIPS)[number];

export const PEER_RELATIONSHIP_LABELS: Record<PeerRelationship, string> = {
	upstream: 'Upstream',
	downstream: 'Downstream',
	uncertain: 'Peer'
};

export const PREFIX_RELATIONSHIPS = ['overlap', 'more_specific', 'less_specific'] as const;
export type PrefixRelationship = (typeof PREFIX_RELATIONSHIPS)[number];

export const PREFIX_RELATIONSHIP_LABELS: Record<PrefixRelationship, string> = {
	overlap: 'Overlapping',
	more_specific: 'More specific',
	less_specific: 'Less specific'
};

export interface AnnouncedPrefixRead {
	prefix: string;
	ip_version: number;
	first_seen: string | null;
	last_seen: string | null;
}

export interface ASNNeighbourRead {
	neighbour_asn: number;
	relationship: PeerRelationship;
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
	relationship: PrefixRelationship;
	origin_asn: number | null;
}
