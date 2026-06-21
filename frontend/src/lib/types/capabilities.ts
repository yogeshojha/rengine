import type { ScanEngine, DiscoveryConfig, ExpansionConfig, DepthConfig } from './scan-engine';
import type { ArtifactType } from './engine';

export type Phase = 'discovery' | 'expansion' | 'depth';

export const PHASE_COLUMN_RANGE: Record<Phase, { min: number; max: number }> = {
	discovery: { min: 1, max: 1 },
	expansion: { min: 2, max: 5 },
	depth: { min: 6, max: 7 }
};

export const CAPABILITY_CONFIG_PHASE: Record<string, Phase> = {
	'dns-whois': 'discovery',
	'related-domains': 'discovery',
	'org-asn': 'discovery',
	'subdomain-enum': 'expansion',
	'cloud-recon': 'expansion',
	'port-scan': 'expansion',
	'http-probe': 'expansion',
	screenshot: 'expansion',
	'url-discovery': 'depth',
	'dir-fuzz': 'depth',
	'param-vhost': 'depth',
	'vuln-scan': 'depth',
	'takeover-dns': 'expansion',
	'js-secrets': 'depth',
	'tls-ssl': 'depth',
	reporting: 'depth'
};

export function configPhaseFor(capabilityId: string, fallback: Phase): Phase {
	return CAPABILITY_CONFIG_PHASE[capabilityId] ?? fallback;
}

export interface StatusPill {
	label: string;
	active: boolean;
}

export interface Capability {
	id: string;
	label: string;
	description: string;
	phase: Phase;
	column: number;
	required: boolean;
	icon: string;
	producesNoun: string;
	produces: ArtifactType;
	consumes: ArtifactType[];
	tools: string[];
	needsKeyTools?: string[];
	isActive: (engine: ScanEngine) => boolean;
	enableFields: Partial<{
		discovery: Partial<DiscoveryConfig>;
		expansion: Partial<ExpansionConfig>;
		depth: Partial<DepthConfig>;
	}>;
	disableFields: Partial<{
		discovery: Partial<DiscoveryConfig>;
		expansion: Partial<ExpansionConfig>;
		depth: Partial<DepthConfig>;
	}>;
	getStatusPills: (engine: ScanEngine) => StatusPill[];
}

export const CAPABILITIES: Capability[] = [
	// ── DISCOVERY PHASE ─────────────────────────────────────────────────────────

	{
		id: 'dns-whois',
		label: 'DNS & WHOIS',
		description: 'Resolve targets, DNS records & WHOIS enrichment',
		phase: 'discovery',
		column: 1,
		required: true,
		icon: 'Globe',
		producesNoun: 'hosts & DNS records',
		produces: 'hosts',
		consumes: ['seed'],
		tools: ['dnsx', 'whois'],
		isActive: (_engine: ScanEngine) => true,
		enableFields: {},
		disableFields: {},
		getStatusPills: (_engine: ScanEngine) => [
			{ label: 'DNS', active: true },
			{ label: 'Reverse DNS', active: true },
			{ label: 'WHOIS', active: true }
		]
	},

	{
		id: 'related-domains',
		label: 'Related Domains',
		description: 'Find related domains via WHOIS, cert SANs & nameservers',
		phase: 'discovery',
		column: 1,
		required: false,
		icon: 'Share2',
		producesNoun: 'related domains',
		produces: 'domains',
		consumes: ['seed'],
		tools: ['whois', 'tlsx', 'cdncheck'],
		needsKeyTools: ['WHOISXML', 'Shodan'],
		isActive: (engine: ScanEngine) => engine.discovery.related_domains_enabled,
		enableFields: {
			discovery: {
				related_domains_enabled: true,
				related_by_whois_registrant: true,
				related_by_cert_san: true,
				related_by_nameservers: true
			}
		},
		disableFields: {
			discovery: {
				related_domains_enabled: false,
				related_by_whois_registrant: false,
				related_by_cert_san: false,
				related_by_nameservers: false,
				related_by_ip_neighbors: false,
				related_by_ga_id: false,
				related_by_favicon_hash: false,
				related_by_asn: false,
				related_tld_variations: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'WHOIS', active: engine.discovery.related_by_whois_registrant },
			{ label: 'Cert SANs', active: engine.discovery.related_by_cert_san },
			{ label: 'Nameservers', active: engine.discovery.related_by_nameservers },
			{ label: 'TLD vars', active: engine.discovery.related_tld_variations }
		]
	},

	{
		id: 'org-asn',
		label: 'Org & ASN',
		description: 'Discover org domains & netblocks via WHOIS, CT & ASN',
		phase: 'discovery',
		column: 1,
		required: false,
		icon: 'Building2',
		producesNoun: 'domains & netblocks',
		produces: 'domains',
		consumes: ['seed'],
		tools: ['amass', 'whois'],
		needsKeyTools: ['WHOISXML'],
		isActive: (engine: ScanEngine) =>
			engine.discovery.org_whois_search ||
			engine.discovery.org_cert_transparency ||
			engine.discovery.org_asn_lookup,
		enableFields: {
			discovery: {
				org_whois_search: true,
				org_cert_transparency: true,
				org_asn_lookup: true
			}
		},
		disableFields: {
			discovery: {
				org_whois_search: false,
				org_cert_transparency: false,
				org_asn_lookup: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Org WHOIS', active: engine.discovery.org_whois_search },
			{ label: 'Cert Transparency', active: engine.discovery.org_cert_transparency },
			{ label: 'ASN', active: engine.discovery.org_asn_lookup }
		]
	},

	// ── EXPANSION PHASE ──────────────────────────────────────────────────────────

	{
		id: 'subdomain-enum',
		label: 'Subdomain Discovery',
		description: 'Passive & active subdomain enumeration',
		phase: 'expansion',
		column: 2,
		required: false,
		icon: 'Search',
		producesNoun: 'subdomains',
		produces: 'subdomains',
		consumes: ['hosts', 'domains'],
		tools: ['subfinder', 'amass', 'tlsx', 'puredns'],
		needsKeyTools: ['Censys', 'SecurityTrails', 'VirusTotal', 'Chaos', 'BinaryEdge'],
		isActive: (engine: ScanEngine) =>
			engine.expansion.subdomain_passive || engine.expansion.subdomain_active,
		enableFields: {
			expansion: {
				subdomain_passive: true,
				subdomain_tls_discovery: true
			}
		},
		disableFields: {
			expansion: {
				subdomain_passive: false,
				subdomain_active: false,
				subdomain_tls_discovery: false,
				subdomain_scraping: false,
				subdomain_permutation: false,
				subdomain_ai_permutation: false,
				subdomain_noerror: false,
				subdomain_recursive: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Passive', active: engine.expansion.subdomain_passive },
			{ label: 'Active', active: engine.expansion.subdomain_active },
			{ label: 'TLS', active: engine.expansion.subdomain_tls_discovery },
			{ label: 'Scraping', active: engine.expansion.subdomain_scraping },
			{ label: 'Permutations', active: engine.expansion.subdomain_permutation }
		]
	},

	{
		id: 'takeover-dns',
		label: 'Subdomain Takeover & DNS',
		description: 'Subdomain takeover & DNS zone transfer checks',
		phase: 'depth',
		column: 6,
		required: false,
		icon: 'Unlink',
		producesNoun: 'takeover findings',
		produces: 'findings',
		consumes: ['subdomains'],
		tools: ['nuclei', 'dnstake', 'dig'],
		isActive: (engine: ScanEngine) =>
			engine.expansion.subdomain_takeover || engine.expansion.dns_zone_transfer,
		enableFields: {
			expansion: {
				subdomain_takeover: true,
				dns_zone_transfer: true
			}
		},
		disableFields: {
			expansion: {
				subdomain_takeover: false,
				dns_zone_transfer: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Takeover', active: engine.expansion.subdomain_takeover },
			{ label: 'Zone Transfer', active: engine.expansion.dns_zone_transfer }
		]
	},

	{
		id: 'cloud-recon',
		label: 'Cloud Recon',
		description: 'Cloud bucket enumeration & reverse IP lookup',
		phase: 'expansion',
		column: 2,
		required: false,
		icon: 'Cloud',
		producesNoun: 'buckets & hostnames',
		produces: 'buckets',
		consumes: ['hosts', 'domains'],
		tools: ['s3scanner', 'cloud_enum', 'hakip2host'],
		needsKeyTools: ['Shodan'],
		isActive: (engine: ScanEngine) =>
			engine.expansion.cloud_bucket_enum || engine.expansion.reverse_ip_lookup,
		enableFields: {
			expansion: {
				cloud_bucket_enum: true,
				reverse_ip_lookup: true
			}
		},
		disableFields: {
			expansion: {
				cloud_bucket_enum: false,
				reverse_ip_lookup: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Bucket Enum', active: engine.expansion.cloud_bucket_enum },
			{ label: 'Reverse IP', active: engine.expansion.reverse_ip_lookup }
		]
	},

	{
		id: 'port-scan',
		label: 'Port Scanning',
		description: 'Discover open ports and services',
		phase: 'expansion',
		column: 3,
		required: false,
		icon: 'Radar',
		producesNoun: 'open ports',
		produces: 'ports',
		consumes: ['subdomains'],
		tools: ['naabu', 'nmap', 'smap'],
		needsKeyTools: ['Shodan'],
		isActive: (engine: ScanEngine) => engine.expansion.port_scan_enabled,
		enableFields: {
			expansion: {
				port_scan_enabled: true
			}
		},
		disableFields: {
			expansion: {
				port_scan_enabled: false,
				nmap_enabled: false,
				port_scan_passive_shodan: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: engine.expansion.port_scan_ports ?? 'top-100', active: engine.expansion.port_scan_enabled },
			{ label: 'Nmap', active: engine.expansion.nmap_enabled },
			{ label: 'Passive', active: engine.expansion.port_scan_passive_shodan }
		]
	},

	{
		id: 'http-probe',
		label: 'HTTP Fingerprinting',
		description: 'Probe HTTP services, WAF, CDN, tech, CMS & vhosts',
		phase: 'expansion',
		column: 4,
		required: false,
		icon: 'Globe2',
		producesNoun: 'live web services',
		produces: 'live-hosts',
		consumes: ['subdomains', 'ports'],
		tools: ['httpx', 'cdncheck', 'wafw00f', 'cmseek'],
		isActive: (engine: ScanEngine) => engine.expansion.http_crawl,
		enableFields: {
			expansion: {
				http_crawl: true,
				cdn_detection: true,
				waf_detection: true,
				tech_detection: true,
				cms_detection: true,
				ip_geolocation: true
			}
		},
		disableFields: {
			expansion: {
				http_crawl: false,
				cdn_detection: false,
				waf_detection: false,
				tech_detection: false,
				cms_detection: false,
				ip_geolocation: false,
				vhost_bruteforce: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'WAF', active: engine.expansion.waf_detection },
			{ label: 'CDN', active: engine.expansion.cdn_detection },
			{ label: 'Tech', active: engine.expansion.tech_detection },
			{ label: 'CMS', active: engine.expansion.cms_detection },
			{ label: 'Geo', active: engine.expansion.ip_geolocation },
			{ label: 'VHost', active: engine.expansion.vhost_bruteforce }
		]
	},

	{
		id: 'screenshot',
		label: 'Screenshot',
		description: 'Capture web screenshots of live hosts',
		phase: 'expansion',
		column: 5,
		required: false,
		icon: 'Camera',
		producesNoun: 'screenshots',
		produces: 'screenshots',
		consumes: ['live-hosts'],
		tools: ['gowitness', 'EyeWitness'],
		isActive: (engine: ScanEngine) => engine.expansion.screenshot,
		enableFields: {
			expansion: {
				screenshot: true
			}
		},
		disableFields: {
			expansion: {
				screenshot: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Screenshot', active: engine.expansion.screenshot }
		]
	},

	{
		id: 'url-discovery',
		label: 'URL & Endpoint Discovery',
		description: 'Crawl & discover endpoints and URLs',
		phase: 'expansion',
		column: 5,
		required: false,
		icon: 'Compass',
		producesNoun: 'endpoints & URLs',
		produces: 'endpoints',
		consumes: ['live-hosts'],
		tools: ['katana', 'gau', 'waybackurls', 'gospider'],
		isActive: (engine: ScanEngine) => engine.depth.url_discovery_enabled,
		enableFields: {
			depth: {
				url_discovery_enabled: true
			}
		},
		disableFields: {
			depth: {
				url_discovery_enabled: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Crawl', active: engine.depth.url_discovery_enabled },
			{ label: 'GF patterns', active: (engine.depth.url_gf_patterns?.length ?? 0) > 0 },
			{ label: 'Dedup', active: engine.depth.url_dedup }
		]
	},

	{
		id: 'dir-fuzz',
		label: 'Directory Fuzzing',
		description: 'Directory & file fuzzing with ffuf',
		phase: 'expansion',
		column: 5,
		required: false,
		icon: 'FolderSearch',
		producesNoun: 'paths & files',
		produces: 'endpoints',
		consumes: ['live-hosts'],
		tools: ['ffuf'],
		isActive: (engine: ScanEngine) => engine.depth.dir_fuzz_enabled,
		enableFields: {
			depth: {
				dir_fuzz_enabled: true
			}
		},
		disableFields: {
			depth: {
				dir_fuzz_enabled: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: engine.depth.dir_fuzz_wordlist || 'wordlist', active: engine.depth.dir_fuzz_enabled },
			{ label: 'Recursion', active: (engine.depth.dir_fuzz_recursive_depth ?? 0) > 0 }
		]
	},

	{
		id: 'param-vhost',
		label: 'Parameter Discovery',
		description: 'Hidden parameter discovery',
		phase: 'expansion',
		column: 5,
		required: false,
		icon: 'SlidersHorizontal',
		producesNoun: 'params',
		produces: 'endpoints',
		consumes: ['live-hosts', 'endpoints'],
		tools: ['x8', 'arjun'],
		isActive: (engine: ScanEngine) => engine.depth.param_discovery,
		enableFields: {
			depth: {
				param_discovery: true
			}
		},
		disableFields: {
			depth: {
				param_discovery: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Params', active: engine.depth.param_discovery }
		]
	},

	// ── DEPTH PHASE ──────────────────────────────────────────────────────────────

	{
		id: 'vuln-scan',
		label: 'Vulnerability Scan',
		description: 'Nuclei templates, CORS, XSS, SQLi, SSRF & more',
		phase: 'depth',
		column: 6,
		required: false,
		icon: 'ShieldAlert',
		producesNoun: 'vulnerabilities',
		produces: 'findings',
		consumes: ['live-hosts', 'endpoints'],
		tools: ['nuclei', 'dalfox', 'sqlmap', 'crlfuzz'],
		isActive: (engine: ScanEngine) =>
			engine.depth.nuclei_enabled || engine.depth.cors_check,
		enableFields: {
			depth: {
				nuclei_enabled: true,
				cors_check: true
			}
		},
		disableFields: {
			depth: {
				nuclei_enabled: false,
				cors_check: false,
				dalfox_enabled: false,
				sqlmap_enabled: false,
				crlfuzz_enabled: false,
				ssrf_enabled: false,
				bypass_403: false,
				http_smuggling: false,
				prototype_pollution: false,
				graphql_detection: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'Nuclei', active: engine.depth.nuclei_enabled },
			{ label: 'CORS', active: engine.depth.cors_check },
			{ label: 'XSS', active: engine.depth.dalfox_enabled },
			{ label: 'SQLi', active: engine.depth.sqlmap_enabled }
		]
	},

	{
		id: 'tls-ssl',
		label: 'TLS / SSL Analysis',
		description: 'TLS/SSL certificate & cipher analysis',
		phase: 'depth',
		column: 6,
		required: false,
		icon: 'Lock',
		producesNoun: 'TLS findings',
		produces: 'findings',
		consumes: ['live-hosts'],
		tools: ['testssl', 'tlsx'],
		isActive: (engine: ScanEngine) => engine.depth.ssl_tls_analysis,
		enableFields: {
			depth: {
				ssl_tls_analysis: true
			}
		},
		disableFields: {
			depth: {
				ssl_tls_analysis: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'TLS/SSL', active: engine.depth.ssl_tls_analysis }
		]
	},

	{
		id: 'js-secrets',
		label: 'JS Secrets',
		description: 'Extract leaked secrets from JavaScript files',
		phase: 'depth',
		column: 6,
		required: false,
		icon: 'KeyRound',
		producesNoun: 'leaked secrets',
		produces: 'findings',
		consumes: ['live-hosts', 'endpoints'],
		tools: ['secretfinder', 'mantra'],
		isActive: (engine: ScanEngine) => engine.depth.js_secret_scan,
		enableFields: {
			depth: {
				js_secret_scan: true
			}
		},
		disableFields: {
			depth: {
				js_secret_scan: false
			}
		},
		getStatusPills: (engine: ScanEngine) => [
			{ label: 'SecretFinder', active: engine.depth.js_secret_scan },
			{ label: 'Mantra', active: engine.depth.js_secret_scan }
		]
	},

	{
		id: 'reporting',
		label: 'Reporting',
		description: 'Export formats, AI summary & notifications',
		phase: 'depth',
		column: 7,
		required: false,
		icon: 'FileText',
		producesNoun: 'report & alerts',
		produces: 'report',
		consumes: ['findings'],
		tools: [],
		isActive: (engine: ScanEngine) => engine.depth.report_enabled,
		enableFields: {
			depth: {
				report_enabled: true
			}
		},
		disableFields: {
			depth: {
				report_enabled: false
			}
		},
		getStatusPills: (engine: ScanEngine) => {
			const formats = engine.depth.report_formats ?? [];
			const formatPills: StatusPill[] = formats.map((f) => ({
				label: f.toUpperCase(),
				active: engine.depth.report_enabled
			}));
			return [
				...formatPills,
				{ label: 'AI', active: engine.depth.report_ai_summary },
				{
					label: 'Notify',
					active:
						engine.depth.report_notify_slack ||
						engine.depth.report_notify_discord ||
						engine.depth.report_notify_telegram
				}
			];
		}
	}
];

export function getActiveCapabilities(engine: ScanEngine): Capability[] {
	return CAPABILITIES.filter((c) => c.isActive(engine));
}

// ─── Recon outputs (terminal "Recon Data" node) ───────────────────────────────
export interface ReconOutput {
	key: string;
	label: string;
	icon: string;
}

export function getReconOutputs(engine: ScanEngine): ReconOutput[] {
	const out: ReconOutput[] = [];
	const push = (cond: boolean, key: string, label: string, icon: string) => {
		if (cond) out.push({ key, label, icon });
	};

	// ── Surface (expansion / discovery outputs) ─────────────────────────────────
	push(true, 'hosts', 'Hosts & IPs', 'Globe');
	push(
		engine.discovery.related_domains_enabled ||
			engine.discovery.org_asn_lookup ||
			engine.discovery.org_whois_search,
		'related',
		'Related Domains',
		'Share2'
	);
	push(
		engine.expansion.subdomain_passive || engine.expansion.subdomain_active,
		'subdomains',
		'Subdomains',
		'Search'
	);
	push(engine.expansion.port_scan_enabled, 'ports', 'Open Ports', 'Radar');
	push(engine.expansion.http_crawl, 'services', 'Live Services', 'Globe2');
	push(engine.expansion.tech_detection, 'tech', 'Technologies', 'Cpu');
	push(engine.expansion.screenshot, 'screenshots', 'Screenshots', 'Camera');
	push(
		engine.depth.url_discovery_enabled || engine.depth.dir_fuzz_enabled,
		'endpoints',
		'Endpoints & URLs',
		'Compass'
	);
	push(engine.depth.param_discovery, 'params', 'Parameters', 'SlidersHorizontal');
	push(
		engine.expansion.cloud_bucket_enum || engine.expansion.reverse_ip_lookup,
		'cloud',
		'Cloud Assets',
		'Cloud'
	);

	// ── Findings (depth outputs) ────────────────────────────────────────────────
	push(engine.expansion.subdomain_takeover, 'takeovers', 'Takeovers', 'Unlink');
	push(engine.depth.js_secret_scan, 'secrets', 'Secrets', 'KeyRound');
	push(engine.depth.ssl_tls_analysis, 'tls', 'TLS / SSL', 'Lock');
	push(
		engine.depth.nuclei_enabled || engine.depth.cors_check,
		'vulns',
		'Vulnerabilities',
		'ShieldAlert'
	);

	// ── Report ──────────────────────────────────────────────────────────────────
	push(engine.depth.report_enabled, 'report', 'Report', 'FileText');

	return out;
}

export function applyEnableCapability(engine: ScanEngine, capId: string): ScanEngine {
	const cap = CAPABILITIES.find((c) => c.id === capId);
	if (!cap) return engine;
	return {
		...engine,
		discovery: { ...engine.discovery, ...(cap.enableFields.discovery ?? {}) },
		expansion: { ...engine.expansion, ...(cap.enableFields.expansion ?? {}) },
		depth: { ...engine.depth, ...(cap.enableFields.depth ?? {}) }
	};
}

export function applyDisableCapability(engine: ScanEngine, capId: string): ScanEngine {
	const cap = CAPABILITIES.find((c) => c.id === capId);
	if (!cap) return engine;
	return {
		...engine,
		discovery: { ...engine.discovery, ...(cap.disableFields.discovery ?? {}) },
		expansion: { ...engine.expansion, ...(cap.disableFields.expansion ?? {}) },
		depth: { ...engine.depth, ...(cap.disableFields.depth ?? {}) }
	};
}
