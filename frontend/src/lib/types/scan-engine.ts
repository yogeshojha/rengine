export type Intensity = 'passive' | 'normal' | 'aggressive';

export interface DiscoveryConfig {
  related_domains_enabled: boolean;
  related_by_whois_registrant: boolean;
  related_by_nameservers: boolean;
  related_by_cert_san: boolean;
  related_by_ip_neighbors: boolean;
  related_by_ga_id: boolean;
  related_by_favicon_hash: boolean;
  related_by_asn: boolean;
  related_tld_variations: boolean;
  related_tlds: string[];
  related_confidence_threshold: number;
  related_require_confirmation: boolean;
  related_action: string;
  org_whois_search: boolean;
  org_cert_transparency: boolean;
  org_asn_lookup: boolean;
  org_custom_patterns: string[];
  org_name_variations: string[];
  asn_scan_mode: string;
  cidr_skip_rfc1918: boolean;
  cidr_skip_cdn_ranges: boolean;
  ip_reverse_dns: boolean;
  ip_vhost_discovery: boolean;
  dns_timeout: number;
  dns_threads: number;
  whois_timeout: number;
}

export interface ExpansionConfig {
  subdomain_passive: boolean;
  subdomain_passive_tools: string[];
  subdomain_securitytrails: boolean;
  subdomain_censys: boolean;
  subdomain_virustotal: boolean;
  subdomain_chaos: boolean;
  subdomain_binaryedge: boolean;
  subdomain_active: boolean;
  subdomain_wordlist: string;
  amass_config: boolean;
  subfinder_config: boolean;
  subdomain_tls_discovery: boolean;
  subdomain_scraping: boolean;
  subdomain_permutation: boolean;
  subdomain_permutation_tools: string[];
  subdomain_ai_permutation: boolean;
  subdomain_noerror: boolean;
  subdomain_recursive: boolean;
  dns_zone_transfer: boolean;
  subdomain_takeover: boolean;
  reverse_ip_lookup: boolean;
  cloud_bucket_enum: boolean;
  port_scan_enabled: boolean;
  port_scan_ports: string;
  port_scan_rate_limit: number;
  port_scan_timeout: number;
  port_scan_threads: number;
  port_scan_passive_shodan: boolean;
  nmap_enabled: boolean;
  nmap_cmd: string | null;
  nmap_script: string | null;
  nmap_script_args: string | null;
  http_crawl: boolean;
  cdn_detection: boolean;
  waf_detection: boolean;
  ip_geolocation: boolean;
  tech_detection: boolean;
  cms_detection: boolean;
  vhost_bruteforce: boolean;
  screenshot: boolean;
  screenshot_timeout: number;
  screenshot_threads: number;
}

export interface DepthConfig {
  dir_fuzz_enabled: boolean;
  dir_fuzz_wordlist: string;
  dir_fuzz_extensions: string[];
  dir_fuzz_recursive_depth: number;
  dir_fuzz_rate_limit: number;
  dir_fuzz_threads: number;
  dir_fuzz_auto_calibration: boolean;
  dir_fuzz_match_status: number[];
  dir_fuzz_timeout: number;
  url_discovery_enabled: boolean;
  url_discovery_tools: string[];
  url_gf_patterns: string[];
  url_dedup: boolean;
  url_dedup_fields: string[];
  url_ignore_extensions: string[];
  url_threads: number;
  js_secret_scan: boolean;
  js_secret_tools: string[];
  param_discovery: boolean;
  param_discovery_tools: string[];
  nuclei_enabled: boolean;
  nuclei_severities: string[];
  nuclei_tags: string[];
  nuclei_templates: string[];
  nuclei_custom_templates: string[];
  nuclei_use_config: boolean;
  nuclei_concurrency: number;
  nuclei_rate_limit: number;
  nuclei_retries: number;
  nuclei_timeout: number;
  dalfox_enabled: boolean;
  crlfuzz_enabled: boolean;
  sqlmap_enabled: boolean;
  ssrf_enabled: boolean;
  cors_check: boolean;
  ssl_tls_analysis: boolean;
  bypass_403: boolean;
  http_smuggling: boolean;
  prototype_pollution: boolean;
  graphql_detection: boolean;
  report_enabled: boolean;
  report_formats: string[];
  report_ai_summary: boolean;
  report_notify_slack: boolean;
  report_notify_discord: boolean;
  report_notify_telegram: boolean;
  report_webhook_url: string | null;
  report_send_on: string;
}

export interface ScanEngine {
  id: string;
  project_id: string;
  created_by: string;
  name: string;
  description: string | null;
  intensity: Intensity;
  global_threads: number;
  global_http_crawl: boolean;
  global_headers: string[];
  discovery: DiscoveryConfig;
  expansion: ExpansionConfig;
  depth: DepthConfig;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
}

export interface ScanEngineCreate {
  name: string;
  description?: string | null;
  intensity?: Intensity;
  global_threads?: number;
  global_http_crawl?: boolean;
  global_headers?: string[];
  discovery?: Partial<DiscoveryConfig>;
  expansion?: Partial<ExpansionConfig>;
  depth?: Partial<DepthConfig>;
}

export interface ScanEngineUpdate {
  name?: string;
  description?: string | null;
  intensity?: Intensity;
  global_threads?: number;
  global_http_crawl?: boolean;
  global_headers?: string[];
  discovery?: Partial<DiscoveryConfig>;
  expansion?: Partial<ExpansionConfig>;
  depth?: Partial<DepthConfig>;
}

export const DEFAULT_DISCOVERY_CONFIG: DiscoveryConfig = {
  related_domains_enabled: false,
  related_by_whois_registrant: true,
  related_by_nameservers: true,
  related_by_cert_san: true,
  related_by_ip_neighbors: false,
  related_by_ga_id: false,
  related_by_favicon_hash: false,
  related_by_asn: false,
  related_tld_variations: false,
  related_tlds: [],
  related_confidence_threshold: 80,
  related_require_confirmation: true,
  related_action: 'flag',
  org_whois_search: false,
  org_cert_transparency: false,
  org_asn_lookup: false,
  org_custom_patterns: [],
  org_name_variations: [],
  asn_scan_mode: 'summary',
  cidr_skip_rfc1918: true,
  cidr_skip_cdn_ranges: true,
  ip_reverse_dns: true,
  ip_vhost_discovery: false,
  dns_timeout: 10,
  dns_threads: 100,
  whois_timeout: 30
};

export const DEFAULT_EXPANSION_CONFIG: ExpansionConfig = {
  subdomain_passive: true,
  subdomain_passive_tools: ['subfinder', 'amass'],
  subdomain_securitytrails: false,
  subdomain_censys: false,
  subdomain_virustotal: false,
  subdomain_chaos: false,
  subdomain_binaryedge: false,
  subdomain_active: false,
  subdomain_wordlist: '',
  amass_config: false,
  subfinder_config: false,
  subdomain_tls_discovery: true,
  subdomain_scraping: false,
  subdomain_permutation: false,
  subdomain_permutation_tools: ['gotator'],
  subdomain_ai_permutation: false,
  subdomain_noerror: false,
  subdomain_recursive: false,
  dns_zone_transfer: false,
  subdomain_takeover: false,
  reverse_ip_lookup: false,
  cloud_bucket_enum: false,
  port_scan_enabled: true,
  port_scan_ports: 'top-100',
  port_scan_rate_limit: 1000,
  port_scan_timeout: 3000,
  port_scan_threads: 50,
  port_scan_passive_shodan: false,
  nmap_enabled: false,
  nmap_cmd: null,
  nmap_script: null,
  nmap_script_args: null,
  http_crawl: true,
  cdn_detection: true,
  waf_detection: true,
  ip_geolocation: true,
  tech_detection: true,
  cms_detection: false,
  vhost_bruteforce: false,
  screenshot: true,
  screenshot_timeout: 15,
  screenshot_threads: 10
};

export const DEFAULT_DEPTH_CONFIG: DepthConfig = {
  dir_fuzz_enabled: false,
  dir_fuzz_wordlist: '',
  dir_fuzz_extensions: ['php', 'html', 'js'],
  dir_fuzz_recursive_depth: 2,
  dir_fuzz_rate_limit: 150,
  dir_fuzz_threads: 50,
  dir_fuzz_auto_calibration: true,
  dir_fuzz_match_status: [200, 301, 302, 403],
  dir_fuzz_timeout: 30,
  url_discovery_enabled: true,
  url_discovery_tools: ['katana', 'waybackurls'],
  url_gf_patterns: [],
  url_dedup: true,
  url_dedup_fields: ['path'],
  url_ignore_extensions: ['png', 'jpg', 'gif', 'svg', 'woff', 'woff2', 'ttf', 'eot', 'ico'],
  url_threads: 50,
  js_secret_scan: false,
  js_secret_tools: ['trufflehog'],
  param_discovery: false,
  param_discovery_tools: ['arjun'],
  nuclei_enabled: true,
  nuclei_severities: ['critical', 'high', 'medium'],
  nuclei_tags: [],
  nuclei_templates: [],
  nuclei_custom_templates: [],
  nuclei_use_config: false,
  nuclei_concurrency: 25,
  nuclei_rate_limit: 150,
  nuclei_retries: 1,
  nuclei_timeout: 10,
  dalfox_enabled: false,
  crlfuzz_enabled: false,
  sqlmap_enabled: false,
  ssrf_enabled: false,
  cors_check: true,
  ssl_tls_analysis: false,
  bypass_403: false,
  http_smuggling: false,
  prototype_pollution: false,
  graphql_detection: false,
  report_enabled: true,
  report_formats: ['pdf'],
  report_ai_summary: false,
  report_notify_slack: false,
  report_notify_discord: false,
  report_notify_telegram: false,
  report_webhook_url: null,
  report_send_on: 'completion'
};
