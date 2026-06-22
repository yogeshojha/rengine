export enum SubdomainSource {
	SUBFINDER = 'subfinder',
	CTFR = 'ctfr',
	SUBLIST3R = 'sublist3r',
	ASSETFINDER = 'assetfinder',
	AMASS = 'amass',
	TLSX = 'tlsx',
	ONEFORALL = 'oneforall',
	NETLAS = 'netlas',
	SUDOMY = 'sudomy',
	SECURITYTRAILS = 'securitytrails',
	CHAOS = 'chaos',
	CENSYS = 'censys',
	VIRUSTOTAL = 'virustotal',
	BINARYEDGE = 'binaryedge',
	BRUTEFORCE = 'bruteforce',
	PERMUTATION = 'permutation',
	ZONE_TRANSFER = 'zone_transfer',
	SCRAPING = 'scraping',
	TLS_CERT = 'tls_cert',
	OTHER = 'other'
}

export interface SubdomainRead {
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
	discovered_at: string;
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
