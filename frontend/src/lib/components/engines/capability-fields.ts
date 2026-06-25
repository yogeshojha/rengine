export type SelectOption = { value: string; label: string };
export type BoolOption = { value: boolean; label: string };

export type FieldSpec =
	| { kind: 'toggle'; label: string; path: string; fallback: boolean }
	| { kind: 'togglekey'; label: string; path: string; fallback: boolean; keyName: string }
	| { kind: 'number'; label: string; path: string; fallback: number }
	| { kind: 'radio'; path: string; fallback: string; options: SelectOption[] }
	| { kind: 'boolradio'; path: string; fallback: boolean; options: BoolOption[] }
	| { kind: 'checkgroup'; path: string; options: SelectOption[] }
	| { kind: 'checkchips'; path: string; values: string[]; upper?: boolean }
	| { kind: 'checkchipsint'; path: string; values: number[] }
	| { kind: 'select'; label: string; path: string; fallback: string; options: SelectOption[] }
	| { kind: 'hint'; text: string }
	| {
			kind: 'text';
			label: string;
			path: string;
			fallback: string;
			placeholder?: string;
			mono?: boolean;
	  }
	| { kind: 'textcsv'; label: string; path: string; placeholder?: string }
	| { kind: 'csv'; path: string }
	| { kind: 'lines'; path: string };

export type Section = { key: string; title: string; fields: FieldSpec[] };

export const CAPABILITY_FIELDS: Record<string, Section[]> = {
	'dns-whois': [
		{
			key: 'dns',
			title: 'DNS Settings',
			fields: [
				{ kind: 'number', label: 'Timeout (s)', path: 'dns_timeout', fallback: 10 },
				{ kind: 'number', label: 'Threads', path: 'dns_threads', fallback: 100 }
			]
		},
		{
			key: 'whois',
			title: 'WHOIS',
			fields: [{ kind: 'number', label: 'Timeout (s)', path: 'whois_timeout', fallback: 30 }]
		},
		{
			key: 'rdns',
			title: 'Reverse DNS',
			fields: [
				{ kind: 'toggle', label: 'Reverse DNS lookups', path: 'ip_reverse_dns', fallback: true }
			]
		}
	],
	'related-domains': [
		{
			key: 'methods',
			title: 'Discovery Methods',
			fields: [
				{
					kind: 'toggle',
					label: 'WHOIS registrant',
					path: 'related_by_whois_registrant',
					fallback: false
				},
				{ kind: 'toggle', label: 'Nameservers', path: 'related_by_nameservers', fallback: false },
				{ kind: 'toggle', label: 'Cert SAN', path: 'related_by_cert_san', fallback: false },
				{ kind: 'toggle', label: 'IP neighbors', path: 'related_by_ip_neighbors', fallback: false },
				{ kind: 'toggle', label: 'Google Analytics ID', path: 'related_by_ga_id', fallback: false },
				{ kind: 'toggle', label: 'Favicon hash', path: 'related_by_favicon_hash', fallback: false },
				{ kind: 'toggle', label: 'ASN', path: 'related_by_asn', fallback: false }
			]
		},
		{
			key: 'tld',
			title: 'TLD Variations',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable TLD variations',
					path: 'related_tld_variations',
					fallback: false
				},
				{ kind: 'hint', text: 'Comma-separated TLDs (e.g. com, net, org)' },
				{ kind: 'csv', path: 'related_tlds' }
			]
		},
		{
			key: 'confidence',
			title: 'Confidence',
			fields: [
				{
					kind: 'number',
					label: 'Threshold (0-100)',
					path: 'related_confidence_threshold',
					fallback: 80
				}
			]
		},
		{
			key: 'confirm',
			title: 'Require Confirmation',
			fields: [
				{
					kind: 'toggle',
					label: 'Confirm before adding',
					path: 'related_require_confirmation',
					fallback: true
				}
			]
		},
		{
			key: 'action',
			title: 'Action',
			fields: [
				{
					kind: 'radio',
					path: 'related_action',
					fallback: 'report_only',
					options: [
						{ value: 'scan', label: 'Scan related domains' },
						{ value: 'report_only', label: 'Report only' }
					]
				}
			]
		}
	],
	'org-asn': [
		{
			key: 'sources',
			title: 'Org Sources',
			fields: [
				{
					kind: 'togglekey',
					label: 'WHOIS org search',
					path: 'org_whois_search',
					fallback: false,
					keyName: 'WHOISXML'
				},
				{
					kind: 'toggle',
					label: 'Certificate transparency',
					path: 'org_cert_transparency',
					fallback: false
				},
				{ kind: 'toggle', label: 'ASN lookup', path: 'org_asn_lookup', fallback: false }
			]
		},
		{
			key: 'variations',
			title: 'Name Variations',
			fields: [
				{ kind: 'hint', text: 'One name variation per line' },
				{ kind: 'lines', path: 'org_name_variations' }
			]
		},
		{
			key: 'patterns',
			title: 'Custom Patterns',
			fields: [
				{ kind: 'hint', text: 'One pattern per line' },
				{ kind: 'lines', path: 'org_custom_patterns' }
			]
		},
		{
			key: 'asn-mode',
			title: 'ASN Scan Mode',
			fields: [
				{
					kind: 'radio',
					path: 'asn_scan_mode',
					fallback: 'smart',
					options: [
						{ value: 'smart', label: 'Smart (recommended)' },
						{ value: 'sample', label: 'Sample' },
						{ value: 'full', label: 'Full scan' }
					]
				}
			]
		},
		{
			key: 'cidr',
			title: 'CIDR Filtering',
			fields: [
				{
					kind: 'toggle',
					label: 'Skip RFC1918 (private ranges)',
					path: 'cidr_skip_rfc1918',
					fallback: true
				},
				{ kind: 'toggle', label: 'Skip CDN ranges', path: 'cidr_skip_cdn_ranges', fallback: true }
			]
		}
	],
	'subdomain-enum': [
		{
			key: 'passive',
			title: 'Passive',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable passive enumeration',
					path: 'subdomain_passive',
					fallback: false
				},
				{
					kind: 'checkgroup',
					path: 'subdomain_passive_tools',
					options: [
						{ value: 'subfinder', label: 'Subfinder' },
						{ value: 'amass', label: 'Amass (passive)' },
						{ value: 'ctfr', label: 'crt.sh (CTFR)' },
						{ value: 'assetfinder', label: 'Assetfinder' }
					]
				},
				{ kind: 'hint', text: 'API-key sources' },
				{
					kind: 'togglekey',
					label: 'SecurityTrails',
					path: 'subdomain_securitytrails',
					fallback: false,
					keyName: 'SecurityTrails'
				},
				{
					kind: 'togglekey',
					label: 'Censys',
					path: 'subdomain_censys',
					fallback: false,
					keyName: 'Censys'
				},
				{
					kind: 'togglekey',
					label: 'VirusTotal',
					path: 'subdomain_virustotal',
					fallback: false,
					keyName: 'VirusTotal'
				},
				{
					kind: 'togglekey',
					label: 'Chaos',
					path: 'subdomain_chaos',
					fallback: false,
					keyName: 'Chaos'
				},
				{
					kind: 'togglekey',
					label: 'BinaryEdge',
					path: 'subdomain_binaryedge',
					fallback: false,
					keyName: 'BinaryEdge'
				}
			]
		},
		{
			key: 'active',
			title: 'Active',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable active brute force',
					path: 'subdomain_active',
					fallback: false
				},
				{
					kind: 'select',
					label: 'Wordlist',
					path: 'subdomain_wordlist',
					fallback: '',
					options: [
						{ value: '', label: 'Default' },
						{ value: 'small', label: 'Small (fast)' },
						{ value: 'medium', label: 'Medium' },
						{ value: 'large', label: 'Large' },
						{ value: 'custom', label: 'Custom' }
					]
				},
				{ kind: 'toggle', label: 'Use Amass config', path: 'amass_config', fallback: false },
				{ kind: 'toggle', label: 'Use Subfinder config', path: 'subfinder_config', fallback: false }
			]
		},
		{
			key: 'tls',
			title: 'TLS Discovery',
			fields: [
				{
					kind: 'toggle',
					label: 'TLS certificate discovery',
					path: 'subdomain_tls_discovery',
					fallback: false
				}
			]
		},
		{
			key: 'scraping',
			title: 'Web Scraping',
			fields: [
				{
					kind: 'toggle',
					label: 'Scrape pages for subdomains',
					path: 'subdomain_scraping',
					fallback: false
				}
			]
		},
		{
			key: 'perm',
			title: 'Permutations',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable permutations',
					path: 'subdomain_permutation',
					fallback: false
				},
				{
					kind: 'checkgroup',
					path: 'subdomain_permutation_tools',
					options: [
						{ value: 'gotator', label: 'Gotator' },
						{ value: 'alterx', label: 'AlterX' },
						{ value: 'dnsgen', label: 'DNSGen' }
					]
				},
				{
					kind: 'toggle',
					label: 'AI-assisted permutation',
					path: 'subdomain_ai_permutation',
					fallback: false
				}
			]
		},
		{
			key: 'dns-tech',
			title: 'DNS Techniques',
			fields: [
				{ kind: 'toggle', label: 'NOERROR detection', path: 'subdomain_noerror', fallback: false },
				{
					kind: 'toggle',
					label: 'Recursive resolution',
					path: 'subdomain_recursive',
					fallback: false
				}
			]
		}
	],
	'takeover-dns': [
		{
			key: 'takeover',
			title: 'Takeover',
			fields: [
				{
					kind: 'toggle',
					label: 'Subdomain takeover check',
					path: 'subdomain_takeover',
					fallback: false
				}
			]
		},
		{
			key: 'zone',
			title: 'Zone Transfer',
			fields: [
				{
					kind: 'toggle',
					label: 'DNS zone transfer (AXFR)',
					path: 'dns_zone_transfer',
					fallback: false
				}
			]
		}
	],
	'cloud-recon': [
		{
			key: 'bucket',
			title: 'Bucket Enumeration',
			fields: [
				{
					kind: 'togglekey',
					label: 'Cloud bucket enumeration',
					path: 'cloud_bucket_enum',
					fallback: false,
					keyName: 'Shodan'
				},
				{
					kind: 'hint',
					text: 'Uses S3Scanner and cloud_enum to find exposed buckets across AWS, GCP, and Azure.'
				}
			]
		},
		{
			key: 'reverse-ip',
			title: 'Reverse IP Lookup',
			fields: [
				{ kind: 'toggle', label: 'Reverse IP lookup', path: 'reverse_ip_lookup', fallback: false },
				{ kind: 'hint', text: 'Resolves co-hosted hostnames per IP via hakip2host.' }
			]
		}
	],
	'port-scan': [
		{
			key: 'ports',
			title: 'Port Range',
			fields: [
				{
					kind: 'radio',
					path: 'port_scan_ports',
					fallback: 'top-100',
					options: [
						{ value: 'top-100', label: 'Top 100 ports (fast)' },
						{ value: 'top-1000', label: 'Top 1000 ports' },
						{ value: 'full', label: 'Full range (1-65535)' }
					]
				},
				{
					kind: 'text',
					label: 'Custom (comma / range)',
					path: 'port_scan_ports',
					fallback: 'top-100',
					placeholder: '80,443,8000-9000',
					mono: true
				}
			]
		},
		{
			key: 'rate',
			title: 'Rate / Timeout / Threads',
			fields: [
				{
					kind: 'number',
					label: 'Rate limit (pkts/s)',
					path: 'port_scan_rate_limit',
					fallback: 1000
				},
				{ kind: 'number', label: 'Timeout (ms)', path: 'port_scan_timeout', fallback: 3000 },
				{ kind: 'number', label: 'Threads', path: 'port_scan_threads', fallback: 50 }
			]
		},
		{
			key: 'passive-ports',
			title: 'Passive (Shodan)',
			fields: [
				{
					kind: 'togglekey',
					label: 'Use Shodan for passive port data',
					path: 'port_scan_passive_shodan',
					fallback: false,
					keyName: 'Shodan'
				}
			]
		},
		{
			key: 'nmap',
			title: 'Nmap',
			fields: [
				{ kind: 'toggle', label: 'Enable Nmap', path: 'nmap_enabled', fallback: false },
				{
					kind: 'text',
					label: 'Command flags',
					path: 'nmap_cmd',
					fallback: '',
					placeholder: '-sV -sC -O',
					mono: true
				},
				{
					kind: 'text',
					label: 'Script',
					path: 'nmap_script',
					fallback: '',
					placeholder: 'vuln,auth',
					mono: true
				},
				{
					kind: 'text',
					label: 'Script args',
					path: 'nmap_script_args',
					fallback: '',
					placeholder: 'script arguments...',
					mono: true
				}
			]
		}
	],
	'http-probe': [
		{
			key: 'probing',
			title: 'Probing',
			fields: [
				{ kind: 'toggle', label: 'HTTP probing & crawl', path: 'http_crawl', fallback: true },
				{
					kind: 'hint',
					text: 'httpx probes live services and records titles, status & favicon hashes.'
				}
			]
		},
		{
			key: 'cdn',
			title: 'CDN Detection',
			fields: [{ kind: 'toggle', label: 'Detect CDN', path: 'cdn_detection', fallback: true }]
		},
		{
			key: 'waf',
			title: 'WAF Detection',
			fields: [{ kind: 'toggle', label: 'Detect WAF', path: 'waf_detection', fallback: true }]
		},
		{
			key: 'geo',
			title: 'IP Geolocation',
			fields: [{ kind: 'toggle', label: 'Geolocate IPs', path: 'ip_geolocation', fallback: false }]
		},
		{
			key: 'tech',
			title: 'Technology Detection',
			fields: [
				{ kind: 'toggle', label: 'Detect tech stack', path: 'tech_detection', fallback: true }
			]
		},
		{
			key: 'cms',
			title: 'CMS Detection',
			fields: [
				{ kind: 'toggle', label: 'Detect CMS', path: 'cms_detection', fallback: false },
				{ kind: 'hint', text: 'CMSeeK fingerprints WordPress, Drupal, Joomla & more.' }
			]
		},
		{
			key: 'probe-vhost',
			title: 'VHost Bruteforce',
			fields: [
				{ kind: 'toggle', label: 'VHost bruteforce', path: 'vhost_bruteforce', fallback: false },
				{
					kind: 'hint',
					text: 'Host-header fuzzing to surface virtual hosts not resolvable via DNS.'
				}
			]
		},
		{
			key: 'favicon',
			title: 'Favicon',
			fields: [
				{
					kind: 'hint',
					text: 'httpx records favicon hashes automatically for related-asset pivots — no extra config.'
				}
			]
		}
	],
	screenshot: [
		{
			key: 'screenshot',
			title: 'Screenshot',
			fields: [
				{ kind: 'toggle', label: 'Capture screenshots', path: 'screenshot', fallback: true },
				{ kind: 'number', label: 'Timeout (s)', path: 'screenshot_timeout', fallback: 15 },
				{ kind: 'number', label: 'Threads', path: 'screenshot_threads', fallback: 10 },
				{ kind: 'hint', text: 'Renders live hosts with gowitness / EyeWitness.' }
			]
		}
	],
	'url-discovery': [
		{
			key: 'url-tools',
			title: 'Tools',
			fields: [
				{
					kind: 'checkgroup',
					path: 'url_discovery_tools',
					options: [
						{ value: 'katana', label: 'Katana' },
						{ value: 'gau', label: 'gau' },
						{ value: 'waybackurls', label: 'Wayback Machine' },
						{ value: 'gospider', label: 'GoSpider' }
					]
				}
			]
		},
		{
			key: 'gf',
			title: 'GF Patterns',
			fields: [
				{
					kind: 'checkchips',
					path: 'url_gf_patterns',
					values: ['sqli', 'ssrf', 'xss', 'lfi', 'rce', 'idor', 'redirect', 'debug']
				}
			]
		},
		{
			key: 'dedup',
			title: 'Deduplication',
			fields: [
				{ kind: 'toggle', label: 'Deduplicate URLs', path: 'url_dedup', fallback: true },
				{
					kind: 'textcsv',
					label: 'Dedup fields (csv)',
					path: 'url_dedup_fields',
					placeholder: 'path,query'
				}
			]
		},
		{
			key: 'url-ignore',
			title: 'Ignore Extensions',
			fields: [
				{
					kind: 'textcsv',
					label: 'Extensions (csv)',
					path: 'url_ignore_extensions',
					placeholder: 'css,png,jpg,gif'
				}
			]
		}
	],
	'dir-fuzz': [
		{
			key: 'fuzz-wordlist',
			title: 'Wordlist',
			fields: [
				{
					kind: 'select',
					label: 'Wordlist',
					path: 'dir_fuzz_wordlist',
					fallback: '',
					options: [
						{ value: '', label: 'Default' },
						{ value: 'small', label: 'Small' },
						{ value: 'medium', label: 'Medium' },
						{ value: 'large', label: 'Large' },
						{ value: 'raft-medium', label: 'Raft Medium' }
					]
				}
			]
		},
		{
			key: 'fuzz-ext',
			title: 'Extensions',
			fields: [
				{
					kind: 'textcsv',
					label: 'Extensions (csv)',
					path: 'dir_fuzz_extensions',
					placeholder: 'php,asp,html,js'
				}
			]
		},
		{
			key: 'fuzz-depth',
			title: 'Recursion Depth',
			fields: [
				{ kind: 'number', label: 'Recursive depth', path: 'dir_fuzz_recursive_depth', fallback: 2 }
			]
		},
		{
			key: 'fuzz-status',
			title: 'Match Status Codes',
			fields: [
				{
					kind: 'checkchipsint',
					path: 'dir_fuzz_match_status',
					values: [200, 201, 204, 301, 302, 307, 401, 403]
				}
			]
		},
		{
			key: 'fuzz-rate',
			title: 'Rate / Threads',
			fields: [
				{ kind: 'number', label: 'Rate limit (req/s)', path: 'dir_fuzz_rate_limit', fallback: 150 },
				{ kind: 'number', label: 'Threads', path: 'dir_fuzz_threads', fallback: 50 }
			]
		},
		{
			key: 'fuzz-calib',
			title: 'Auto-calibration',
			fields: [
				{
					kind: 'toggle',
					label: 'Auto-calibration',
					path: 'dir_fuzz_auto_calibration',
					fallback: true
				}
			]
		}
	],
	'param-vhost': [
		{
			key: 'param',
			title: 'Parameter Discovery',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable parameter discovery',
					path: 'param_discovery',
					fallback: false
				},
				{
					kind: 'checkgroup',
					path: 'param_discovery_tools',
					options: [
						{ value: 'x8', label: 'x8' },
						{ value: 'arjun', label: 'Arjun' }
					]
				},
				{ kind: 'hint', text: 'Surfaces hidden GET/POST parameters on discovered endpoints.' }
			]
		}
	],
	'vuln-scan': [
		{
			key: 'nuclei',
			title: 'Nuclei',
			fields: [
				{ kind: 'toggle', label: 'Enable Nuclei', path: 'nuclei_enabled', fallback: true },
				{ kind: 'hint', text: 'Severity' },
				{
					kind: 'checkchips',
					path: 'nuclei_severities',
					values: ['unknown', 'info', 'low', 'medium', 'high', 'critical']
				},
				{ kind: 'textcsv', label: 'Tags (csv)', path: 'nuclei_tags', placeholder: 'cve,oast,rce' },
				{ kind: 'hint', text: 'Templates' },
				{
					kind: 'boolradio',
					path: 'nuclei_use_config',
					fallback: false,
					options: [
						{ value: false, label: 'Default templates' },
						{ value: true, label: 'Custom config' }
					]
				},
				{ kind: 'number', label: 'Concurrency', path: 'nuclei_concurrency', fallback: 25 },
				{ kind: 'number', label: 'Rate limit (req/s)', path: 'nuclei_rate_limit', fallback: 150 },
				{ kind: 'number', label: 'Retries', path: 'nuclei_retries', fallback: 1 },
				{ kind: 'number', label: 'Timeout (s)', path: 'nuclei_timeout', fallback: 10 }
			]
		},
		{
			key: 'cors',
			title: 'CORS',
			fields: [
				{ kind: 'toggle', label: 'CORS misconfiguration', path: 'cors_check', fallback: false }
			]
		},
		{
			key: 'xss',
			title: 'XSS',
			fields: [
				{ kind: 'toggle', label: 'Dalfox XSS scanner', path: 'dalfox_enabled', fallback: false }
			]
		},
		{
			key: 'other',
			title: 'Other Scanners',
			fields: [
				{
					kind: 'toggle',
					label: 'CRLFuzz (CRLF injection)',
					path: 'crlfuzz_enabled',
					fallback: false
				},
				{
					kind: 'toggle',
					label: 'SQLMap (SQL injection)',
					path: 'sqlmap_enabled',
					fallback: false
				},
				{ kind: 'toggle', label: 'SSRF check', path: 'ssrf_enabled', fallback: false },
				{ kind: 'toggle', label: '403 bypass', path: 'bypass_403', fallback: false },
				{ kind: 'toggle', label: 'HTTP smuggling', path: 'http_smuggling', fallback: false },
				{
					kind: 'toggle',
					label: 'Prototype pollution',
					path: 'prototype_pollution',
					fallback: false
				},
				{
					kind: 'toggle',
					label: 'GraphQL introspection',
					path: 'graphql_detection',
					fallback: false
				}
			]
		}
	],
	'tls-ssl': [
		{
			key: 'tls-ssl',
			title: 'TLS / SSL Analysis',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable TLS/SSL analysis',
					path: 'ssl_tls_analysis',
					fallback: false
				},
				{
					kind: 'hint',
					text: 'Inspects certificate chain, weak ciphers, expiry & HSTS via testssl / tlsx.'
				}
			]
		}
	],
	'js-secrets': [
		{
			key: 'js-tools',
			title: 'Tools',
			fields: [
				{
					kind: 'toggle',
					label: 'Enable JS secret scanning',
					path: 'js_secret_scan',
					fallback: false
				},
				{
					kind: 'checkgroup',
					path: 'js_secret_tools',
					options: [
						{ value: 'secretfinder', label: 'SecretFinder' },
						{ value: 'mantra', label: 'Mantra' }
					]
				}
			]
		}
	],
	reporting: [
		{
			key: 'report-formats',
			title: 'Formats',
			fields: [
				{
					kind: 'checkchips',
					path: 'report_formats',
					values: ['html', 'json', 'csv', 'pdf'],
					upper: true
				}
			]
		},
		{
			key: 'report-ai',
			title: 'AI Summary',
			fields: [
				{
					kind: 'toggle',
					label: 'AI-powered executive summary',
					path: 'report_ai_summary',
					fallback: false
				}
			]
		},
		{
			key: 'report-notify',
			title: 'Notifications',
			fields: [
				{ kind: 'toggle', label: 'Slack', path: 'report_notify_slack', fallback: false },
				{ kind: 'toggle', label: 'Discord', path: 'report_notify_discord', fallback: false },
				{ kind: 'toggle', label: 'Telegram', path: 'report_notify_telegram', fallback: false },
				{
					kind: 'text',
					label: 'Webhook URL',
					path: 'report_webhook_url',
					fallback: '',
					placeholder: 'https://hooks.example.com/...',
					mono: false
				}
			]
		},
		{
			key: 'report-on',
			title: 'Send On',
			fields: [
				{
					kind: 'radio',
					path: 'report_send_on',
					fallback: 'completion',
					options: [
						{ value: 'completion', label: 'Scan completion' },
						{ value: 'each_phase', label: 'Each phase' },
						{ value: 'both', label: 'Both' }
					]
				}
			]
		}
	]
};
