export interface DomainPostureRead {
	id: string;
	scan_id: string;
	target_id: string;
	zone: string;
	hosts: number;
	spf: string | null;
	spf_all: string | null;
	spf_lookups: number | null;
	dmarc: string | null;
	dmarc_policy: string | null;
	dmarc_subdomain_policy: string | null;
	dmarc_pct: number | null;
	dmarc_rua: boolean | null;
	dkim_selectors: string[];
	dkim_key_bits: number | null;
	mx: string[];
	null_mx: boolean;
	mta_sts: string | null;
	mta_sts_mode: string | null;
	tls_rpt: string | null;
	dnssec: string;
	caa: string[];
	posture_issues: string[];
	posture_checked: string[];
	evidence: Record<string, string>;
	discovered_at: string;
}

export interface PostureCheckCount {
	key: string;
	failing: number;
	applicable: number;
	query: string;
}

export interface DomainPostureSummary {
	covered: boolean;
	scan_id: string | null;
	target_id: string | null;
	observed_at: string | null;
	zones: DomainPostureRead[];
	evaluated: number;
	clean: number;
	warning: number;
	info: number;
	spoofable: number;
	hosts: number;
	checks: PostureCheckCount[];
}
