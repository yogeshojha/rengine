export interface OriginEvidence {
	kind: string;
	label: string;
	value: string;
}

export interface OriginSample {
	host: string;
	url: string;
	ip: string | null;
	port: number;
	status_code: number | null;
	title: string | null;
	webserver: string | null;
	cdn_name: string | null;
	asn_org: string | null;
	screenshot_path: string | null;
}

export interface OriginFinding {
	kind: string;
	confidence: string;
	exposed: OriginSample;
	fronted: OriginSample[];
	fronted_total: number;
	evidence: OriginEvidence[];
	open_ports: number[];
	sensitive_ports: number[];
	query: string;
}

export interface OriginExposure {
	findings: OriginFinding[];
	probed_addresses: number;
	fronted_assets: number;
}

// mirrors api/app/services/origin_exposure.py
export const ORIGIN_EXPOSED = 'origin_exposed';
export const DEFAULT_VHOST = 'default_vhost';

export const FINDING_TITLE: Record<string, string> = {
	[ORIGIN_EXPOSED]: 'Origin reachable outside the CDN',
	[DEFAULT_VHOST]: 'Address serving a different site'
};

export const FINDING_SUMMARY: Record<string, string> = {
	[ORIGIN_EXPOSED]:
		'The same application answers on an address the CDN does not front. Requests sent to the address are not filtered by the CDN.',
	[DEFAULT_VHOST]: 'The address returns different content when requested without a hostname.'
};

export const FINDING_RELATION: Record<string, string> = {
	[ORIGIN_EXPOSED]: 'Same application',
	[DEFAULT_VHOST]: 'Different content'
};

export function frontedLabel(f: OriginFinding): string {
	const cdn = f.fronted.find((s) => s.cdn_name)?.cdn_name;
	return cdn ?? 'a CDN';
}

export function networkLabel(s: OriginSample): string {
	return s.asn_org ?? s.cdn_name ?? '';
}
