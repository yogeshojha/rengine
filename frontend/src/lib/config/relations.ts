export enum TargetRelation {
	CERTIFICATE = 'certificate',
	REGISTRANT = 'registrant_name',
	NETWORK = 'network',
	NAMESERVER = 'nameserver',
	NETWORK_CIDR = 'network_cidr',
	FAVICON = 'favicon'
}

// strongest first
export const RELATION_ORDER: readonly string[] = [
	TargetRelation.CERTIFICATE,
	TargetRelation.REGISTRANT,
	TargetRelation.NETWORK,
	TargetRelation.NAMESERVER,
	TargetRelation.NETWORK_CIDR,
	TargetRelation.FAVICON
];

export const RELATION_LABELS: Record<string, string> = {
	[TargetRelation.CERTIFICATE]: 'Certificate',
	[TargetRelation.REGISTRANT]: 'Registrant',
	[TargetRelation.NETWORK]: 'Network',
	[TargetRelation.NAMESERVER]: 'Nameserver',
	[TargetRelation.NETWORK_CIDR]: 'Network block',
	[TargetRelation.FAVICON]: 'Favicon'
};

export const RELATION_HELP: Record<string, string> = {
	[TargetRelation.CERTIFICATE]: 'One certificate names both targets',
	[TargetRelation.REGISTRANT]: 'Registered to the same name',
	[TargetRelation.NETWORK]: 'Addresses in a network the organisation runs',
	[TargetRelation.NAMESERVER]: 'Answered by the same nameserver',
	[TargetRelation.NETWORK_CIDR]: 'Inside the same registered network block',
	[TargetRelation.FAVICON]: 'Serving the same favicon'
};
