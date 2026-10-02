export enum TargetRelation {
	CERTIFICATE = 'certificate',
	REGISTRANT = 'registrant_name',
	NETWORK = 'network',
	NAMESERVER = 'nameserver',
	DNS_RECORD = 'dns_record',
	NETWORK_CIDR = 'network_cidr',
	FAVICON = 'favicon'
}

export const RELATION_HELP: Record<string, string> = {
	[TargetRelation.CERTIFICATE]: 'One certificate names both targets',
	[TargetRelation.REGISTRANT]: 'Registered to the same name',
	[TargetRelation.NETWORK]: 'Addresses in a network the organization runs',
	[TargetRelation.NAMESERVER]: 'Answered by the same nameserver',
	[TargetRelation.DNS_RECORD]: 'The same unshared DNS record on both targets',
	[TargetRelation.NETWORK_CIDR]: 'Inside the same registered network block',
	[TargetRelation.FAVICON]: 'Serving the same favicon'
};
