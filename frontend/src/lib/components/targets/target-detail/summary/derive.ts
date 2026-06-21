import type { Target } from '$lib/types/target';
import type { TargetDetailRead, DnsRecordRead } from '$lib/types/target-detail';
import { TargetType } from '$lib/types/target';
import { TaskStatus } from '$lib/types/task-status';
import {
	getExpirationUrgency,
	formatExpirationLabel,
	getDomainAge,
	formatShortDate
} from '$lib/utilities/dates';

export type Tone = 'neutral' | 'good' | 'warn' | 'bad' | 'info';
export type VitalIcon =
	| 'route'
	| 'server'
	| 'globe'
	| 'building'
	| 'calendar'
	| 'shield'
	| 'mail'
	| 'hash'
	| 'network'
	| 'mappin'
	| 'fingerprint'
	| 'radio'
	| 'lock'
	| 'flag';

export interface Vital {
	key: string;
	label: string;
	value: string;
	sub?: string;
	mono?: boolean;
	tone?: Tone;
	icon?: VitalIcon;
	copy?: string;
}

export type PostureStatus = 'pass' | 'warn' | 'fail' | 'info' | 'pending';
export interface PostureItem {
	key: string;
	status: PostureStatus;
	label: string;
	detail?: string;
}

export interface InfraEntry {
	kind: 'ipv4' | 'ipv6' | 'ns' | 'mx';
	value: string;
	note?: string;
}

export interface TargetSummary {
	vitals: Vital[];
	posture: PostureItem[];
	infra: InfraEntry[];
}

const isDomainLike = (t: TargetType) => t === TargetType.DOMAIN || t === TargetType.URL;
const isNetwork = (t: TargetType) =>
	t === TargetType.IP || t === TargetType.IP_RANGE || t === TargetType.ASN;

function recordsOfType(records: DnsRecordRead[], type: string): DnsRecordRead[] {
	return records.filter((r) => r.record_type === type);
}

const NS_PROVIDERS: ReadonlyArray<readonly [RegExp, string]> = [
	[/cloudflare/i, 'Cloudflare'],
	[/(awsdns|route53|amazonaws)/i, 'AWS Route 53'],
	[/(domaincontrol|godaddy)/i, 'GoDaddy'],
	[/(googledomains|ns[.-]google|google\.com)/i, 'Google'],
	[/(azure-dns|azuredns)/i, 'Azure DNS'],
	[/(akam\.net|akamai)/i, 'Akamai'],
	[/dnsmadeeasy/i, 'DNS Made Easy'],
	[/(\bns1\b|nsone\.net)/i, 'NS1'],
	[/dyn(ect)?\.(com|net)/i, 'Dyn'],
	[/digitalocean/i, 'DigitalOcean'],
	[/(registrar-servers|namecheap|name-services)/i, 'Namecheap'],
	[/buddyns/i, 'BuddyNS'],
	[/vercel-dns/i, 'Vercel'],
	[/fastly/i, 'Fastly'],
	[/(hover|tucows)/i, 'Tucows'],
	[/wordpress|wpengine/i, 'WordPress'],
	[/gandi/i, 'Gandi']
];

function detectProvider(hosts: string[]): string | null {
	for (const h of hosts) {
		for (const [re, name] of NS_PROVIDERS) if (re.test(h)) return name;
	}
	return null;
}

function spfPolicy(spf: string): { label: string; tone: Tone } {
	if (/-all/.test(spf)) return { label: 'strict (-all)', tone: 'good' };
	if (/~all/.test(spf)) return { label: 'soft-fail (~all)', tone: 'warn' };
	if (/\?all/.test(spf)) return { label: 'neutral (?all)', tone: 'warn' };
	if (/\+all/.test(spf)) return { label: 'permissive (+all)', tone: 'bad' };
	return { label: 'present', tone: 'good' };
}

const VERIFICATION_TOKENS: ReadonlyArray<readonly [RegExp, string]> = [
	[/^google-site-verification=/i, 'Google'],
	[/^MS=/i, 'Microsoft 365'],
	[/^apple-domain-verification=/i, 'Apple'],
	[/^facebook-domain-verification=/i, 'Meta'],
	[/^atlassian-/i, 'Atlassian'],
	[/^docusign=/i, 'DocuSign'],
	[/^stripe-verification=/i, 'Stripe'],
	[/^adobe-/i, 'Adobe'],
	[/^_?amazonses|^amazonses:/i, 'Amazon SES'],
	[/^zoom-/i, 'Zoom'],
	[/^miro-verification=/i, 'Miro'],
	[/^notion-/i, 'Notion']
];

const LOCK_HINTS = ['transferprohibited', 'deleteprohibited', 'updateprohibited', 'renewprohibited'];

function toneFromUrgency(u: ReturnType<typeof getExpirationUrgency>): Tone {
	if (u === 'expired') return 'bad';
	if (u === 'critical') return 'warn';
	if (u === 'warning') return 'warn';
	if (u === 'healthy') return 'good';
	return 'neutral';
}

function pendingFor(status: TaskStatus): boolean {
	return status === TaskStatus.PENDING || status === TaskStatus.QUERYING;
}

function buildDomain(target: Target, detail: TargetDetailRead | null): TargetSummary {
	const vitals: Vital[] = [];
	const posture: PostureItem[] = [];
	const infra: InfraEntry[] = [];

	const dns = detail?.dns ?? null;
	const records = dns?.records ?? [];
	const whois = detail?.whois ?? null;
	const wsum = target.whois;
	const registrarName = whois?.registrar_name || wsum?.registrar_name || '';
	const registrantName = whois?.registrant_name || wsum?.registrant_name || '';
	const registrationDate = whois?.registration_date || wsum?.registration_date || null;
	const expirationDate = whois?.expiration_date || wsum?.expiration_date || null;
	const dnsStatus = target.dns_status;
	const whoisStatus = target.whois_status;

	const aRecs = recordsOfType(records, 'A');
	const aaaaRecs = recordsOfType(records, 'AAAA');
	const cnameRecs = recordsOfType(records, 'CNAME');
	const nsRecs = recordsOfType(records, 'NS');
	const mxRecs = recordsOfType(records, 'MX');
	const txtRecs = recordsOfType(records, 'TXT');

	const ips = [...aRecs, ...aaaaRecs].map((r) => r.value);
	if (aRecs.length || aaaaRecs.length) {
		const primary = aRecs[0]?.value ?? aaaaRecs[0]?.value ?? '';
		const extra = ips.length - 1;
		vitals.push({
			key: 'resolves',
			label: 'Resolves to',
			value: primary,
			sub: extra > 0 ? `+${extra} more address${extra > 1 ? 'es' : ''}` : 'single address',
			mono: true,
			icon: 'route',
			copy: primary
		});
	} else if (cnameRecs.length) {
		vitals.push({
			key: 'resolves',
			label: 'Resolves to',
			value: cnameRecs[0].value,
			sub: 'CNAME alias',
			mono: true,
			icon: 'route',
			copy: cnameRecs[0].value
		});
	} else if (dnsStatus === TaskStatus.SUCCESS) {
		vitals.push({ key: 'resolves', label: 'Resolves to', value: 'No A/AAAA record', tone: 'warn', icon: 'route' });
	}
	for (const r of aRecs) infra.push({ kind: 'ipv4', value: r.value });
	for (const r of aaaaRecs) infra.push({ kind: 'ipv6', value: r.value });

	const nsHosts = nsRecs.map((r) => r.value);
	const nsProvider = detectProvider(nsHosts) ?? (whois?.nameservers ? detectProvider(whois.nameservers) : null);
	if (nsHosts.length || nsProvider) {
		vitals.push({
			key: 'auth-dns',
			label: 'Authoritative DNS',
			value: nsProvider ?? `${nsHosts.length} nameservers`,
			sub: nsProvider && nsHosts.length ? `${nsHosts.length} NS records` : undefined,
			icon: 'server'
		});
	}
	for (const ns of nsHosts) infra.push({ kind: 'ns', value: ns });

	if (dns?.cdn) {
		vitals.push({
			key: 'cdn',
			label: 'Edge / CDN',
			value: dns.cdn_name || 'CDN detected',
			sub: 'fronted by edge network',
			tone: 'info',
			icon: 'globe'
		});
	}

	if (whoisStatus === TaskStatus.FAILED) {
		vitals.push({ key: 'registrar', label: 'Registrar', value: 'Unavailable', sub: 'WHOIS lookup failed', tone: 'warn', icon: 'building' });
	} else if (registrarName) {
		vitals.push({
			key: 'registrar',
			label: 'Registrar',
			value: registrarName,
			sub: registrantName || undefined,
			icon: 'building'
		});
	}

	if (expirationDate) {
		const urg = getExpirationUrgency(expirationDate);
		vitals.push({
			key: 'expiry',
			label: 'Registration',
			value: formatExpirationLabel(expirationDate),
			sub: registrationDate ? getDomainAge(registrationDate) : formatShortDate(expirationDate),
			tone: toneFromUrgency(urg),
			icon: 'calendar'
		});
	}

	if (whois && whois.dnssec != null) {
		vitals.push({
			key: 'dnssec',
			label: 'DNSSEC',
			value: whois.dnssec ? 'Enabled' : 'Not enabled',
			tone: whois.dnssec ? 'good' : 'warn',
			icon: 'shield'
		});
	}

	const spf = txtRecs.map((r) => r.value).find((v) => v.toLowerCase().startsWith('v=spf1'));
	if (spf) {
		const pol = spfPolicy(spf);
		vitals.push({ key: 'email', label: 'Email auth (SPF)', value: pol.label, tone: pol.tone, icon: 'mail' });
	} else if (dnsStatus === TaskStatus.SUCCESS) {
		vitals.push({
			key: 'email',
			label: 'Email auth (SPF)',
			value: 'No SPF record',
			tone: mxRecs.length ? 'warn' : 'neutral',
			sub: mxRecs.length ? 'mail configured' : 'no mail records',
			icon: 'mail'
		});
	}

	if (dnsStatus === TaskStatus.SUCCESS) {
		const counts = target.dns?.record_counts ?? {};
		const total = records.length || Object.values(counts).reduce((a, b) => a + b, 0);
		const breakdown = Object.entries(counts)
			.filter(([, n]) => n > 0)
			.sort((a, b) => b[1] - a[1])
			.slice(0, 4)
			.map(([t, n]) => `${t} ${n}`)
			.join(' · ');
		vitals.push({
			key: 'dns-count',
			label: 'DNS records',
			value: String(total),
			sub: breakdown || undefined,
			icon: 'network'
		});
	}

	for (const r of mxRecs) infra.push({ kind: 'mx', value: r.value, note: r.priority != null ? `priority ${r.priority}` : undefined });

	if (pendingFor(whoisStatus)) {
		posture.push({ key: 'whois', status: 'pending', label: 'Registration lookup in progress' });
	} else if (whoisStatus === TaskStatus.FAILED) {
		posture.push({
			key: 'whois',
			status: 'warn',
			label: 'Registration data unavailable',
			detail: target.whois_error ? shortError(target.whois_error) : 'WHOIS/RDAP lookup failed'
		});
	} else if (expirationDate) {
		const urg = getExpirationUrgency(expirationDate);
		if (urg === 'expired')
			posture.push({ key: 'whois', status: 'fail', label: 'Domain registration expired', detail: formatShortDate(expirationDate) });
		else if (urg === 'critical')
			posture.push({ key: 'whois', status: 'warn', label: formatExpirationLabel(expirationDate), detail: 'renew soon to avoid loss' });
		else posture.push({ key: 'whois', status: 'pass', label: 'Registration in good standing', detail: formatExpirationLabel(expirationDate) });
	}

	if (whois && whois.dnssec != null) {
		posture.push(
			whois.dnssec
				? { key: 'dnssec', status: 'pass', label: 'DNSSEC enabled' }
				: { key: 'dnssec', status: 'warn', label: 'DNSSEC not enabled', detail: 'responses are not cryptographically signed' }
		);
	}

	if (spf) {
		const pol = spfPolicy(spf);
		posture.push({
			key: 'spf',
			status: pol.tone === 'good' ? 'pass' : 'warn',
			label: `SPF policy ${pol.label}`,
			detail: pol.tone === 'good' ? undefined : 'weak sender policy permits spoofing'
		});
	} else if (dnsStatus === TaskStatus.SUCCESS && mxRecs.length) {
		posture.push({ key: 'spf', status: 'warn', label: 'No SPF record', detail: 'mail is configured but sender policy is missing' });
	}

	const locks = (whois?.domain_status ?? []).filter((s) =>
		LOCK_HINTS.some((h) => s.toLowerCase().replace(/\s+/g, '').includes(h))
	);
	if (whois?.domain_status?.length) {
		posture.push(
			locks.length
				? { key: 'lock', status: 'pass', label: `Registrar locks active (${locks.length})`, detail: 'transfer/delete protections set' }
				: { key: 'lock', status: 'info', label: 'No transfer locks visible' }
		);
	}

	if (pendingFor(dnsStatus)) posture.push({ key: 'dns', status: 'pending', label: 'DNS resolution in progress' });
	else if (dnsStatus === TaskStatus.FAILED)
		posture.push({ key: 'dns', status: 'fail', label: 'DNS resolution failed', detail: target.dns_error ? shortError(target.dns_error) : undefined });

	if (dns?.cdn) posture.push({ key: 'cdn', status: 'info', label: `Fronted by ${dns.cdn_name || 'a CDN'}`, detail: 'origin shielded behind edge network' });

	const verifs = new Set<string>();
	for (const v of txtRecs.map((r) => r.value)) {
		for (const [re, name] of VERIFICATION_TOKENS) if (re.test(v)) verifs.add(name);
	}
	if (verifs.size)
		posture.push({ key: 'verif', status: 'info', label: `${verifs.size} service verification${verifs.size > 1 ? 's' : ''}`, detail: [...verifs].join(', ') });

	return { vitals, posture, infra };
}

function buildNetwork(target: Target, detail: TargetDetailRead | null): TargetSummary {
	const vitals: Vital[] = [];
	const posture: PostureItem[] = [];
	const infra: InfraEntry[] = [];

	const bgp = detail?.bgp ?? null;
	const whois = detail?.whois ?? null;
	const wsum = target.whois;
	const bgpStatus = target.bgp_status;
	const t = target.target_type;

	const as = bgp?.as_overview ?? null;
	const VALID_RIR = /^(arin|ripe|apnic|lacnic|afrinic)/i;
	const rir = [whois?.rir, as?.rir].map((x) => (x || '').trim()).find((x) => VALID_RIR.test(x)) || '';
	const neigh = bgp?.neighbours ?? [];
	const upstream = neigh.filter((n) => n.relationship === 'upstream');
	const downstream = neigh.filter((n) => n.relationship === 'downstream');
	const prefixCount = bgp?.announced_prefixes?.length || target.bgp?.prefix_count || 0;
	const peerCount = neigh.length || target.bgp?.peer_count || 0;

	if (t === TargetType.ASN) {
		const holder = as?.holder || target.bgp?.holder || whois?.name;
		if (holder) vitals.push({ key: 'holder', label: 'AS holder', value: holder, icon: 'building' });
		const announced = as?.announced ?? target.bgp?.announced;
		if (announced != null)
			vitals.push({ key: 'announced', label: 'Routing', value: announced ? 'Announced' : 'Not announced', tone: announced ? 'good' : 'warn', icon: 'radio' });
		if (prefixCount) vitals.push({ key: 'prefixes', label: 'Announced prefixes', value: String(prefixCount), icon: 'network' });
		if (peerCount)
			vitals.push({ key: 'peers', label: 'BGP peers', value: String(peerCount), sub: `${upstream.length} up · ${downstream.length} down`, icon: 'route' });
		const topUpstream = upstream.length ? [...upstream].sort((a, b) => (b.power ?? 0) - (a.power ?? 0))[0] : null;
		if (topUpstream)
			vitals.push({ key: 'upstream', label: 'Primary upstream', value: `AS${topUpstream.neighbour_asn}`, mono: true, icon: 'radio', copy: `AS${topUpstream.neighbour_asn}` });
		if (rir) vitals.push({ key: 'rir', label: 'Registry (RIR)', value: rir.toUpperCase(), icon: 'flag' });
		if (as?.block_resource) vitals.push({ key: 'block', label: 'Allocation block', value: as.block_resource, sub: as.block_name || undefined, mono: true, icon: 'hash' });
	} else {
		const originAsn = as?.asn || target.bgp?.asn || bgp?.network_info?.[0]?.asn || bgp?.prefix_overview?.[0]?.asn;
		const holder = as?.holder || target.bgp?.holder || bgp?.prefix_overview?.[0]?.holder || whois?.name;
		if (originAsn)
			vitals.push({ key: 'asn', label: 'Origin AS', value: `AS${originAsn}`, sub: holder || undefined, mono: true, icon: 'route', copy: `AS${originAsn}` });
		else if (whois?.name)
			vitals.push({ key: 'netname', label: 'Network name', value: whois.name, icon: 'building' });
		const prefix =
			target.bgp?.prefix || bgp?.network_info?.[0]?.prefix || bgp?.prefix_overview?.[0]?.prefix || whois?.network_cidr || wsum?.network_cidr;
		if (prefix) vitals.push({ key: 'prefix', label: 'Covering prefix', value: prefix, mono: true, icon: 'network', copy: prefix });
		const announced = bgp?.prefix_overview?.[0]?.is_announced ?? target.bgp?.announced;
		if (announced != null)
			vitals.push({ key: 'announced', label: 'Routing', value: announced ? 'Announced' : 'Not announced', tone: announced ? 'good' : 'warn', icon: 'radio' });
		if (t === TargetType.IP_RANGE && bgp?.related_prefixes?.length)
			vitals.push({ key: 'related', label: 'Related prefixes', value: String(bgp.related_prefixes.length), icon: 'hash' });
		if (rir) vitals.push({ key: 'rir', label: 'Registry (RIR)', value: rir.toUpperCase(), icon: 'flag' });
		if (whois?.assignment_type) vitals.push({ key: 'assign', label: 'Assignment', value: whois.assignment_type, icon: 'fingerprint' });
		if (whois?.ip_version) vitals.push({ key: 'ipv', label: 'IP version', value: `IPv${whois.ip_version}`, icon: 'hash' });
	}

	const country = whois?.country || wsum?.country;
	if (country) vitals.push({ key: 'country', label: 'Country', value: country, icon: 'mappin' });

	const abuse = bgp?.abuse_contacts?.[0]?.abuse_email || whois?.abuse_email;
	if (abuse) vitals.push({ key: 'abuse', label: 'Abuse contact', value: abuse, mono: true, icon: 'mail', copy: abuse });

	if (pendingFor(bgpStatus)) {
		posture.push({ key: 'bgp', status: 'pending', label: 'BGP enrichment in progress' });
	} else if (bgpStatus === TaskStatus.FAILED) {
		posture.push({ key: 'bgp', status: 'fail', label: 'BGP enrichment failed' });
	} else {
		const announced =
			t === TargetType.ASN
				? (as?.announced ?? target.bgp?.announced)
				: (bgp?.prefix_overview?.[0]?.is_announced ?? target.bgp?.announced);
		if (announced === false) posture.push({ key: 'announced', status: 'warn', label: 'Not announced in the global routing table', detail: 'no visible BGP route' });
		else if (announced === true) posture.push({ key: 'announced', status: 'pass', label: 'Announced in BGP', detail: 'visible in the global routing table' });
	}

	if (t === TargetType.ASN && peerCount) {
		const downRatio = peerCount ? downstream.length / peerCount : 0;
		const upRatio = peerCount ? upstream.length / peerCount : 0;
		const pos =
			downRatio > 0.6
				? 'Transit provider — significant downstream customer base'
				: upRatio > 0.6
					? 'Leaf network — primarily consumes transit'
					: 'Mid-tier network — balanced peering';
		posture.push({ key: 'position', status: 'info', label: pos });
	}

	if (abuse) posture.push({ key: 'abuse', status: 'pass', label: 'Abuse contact published', detail: abuse });
	else if (bgpStatus === TaskStatus.SUCCESS) posture.push({ key: 'abuse', status: 'info', label: 'No abuse contact found' });

	for (const ni of bgp?.network_info ?? []) infra.push({ kind: 'ipv4', value: ni.ip, note: ni.prefix });

	if (bgpStatus === TaskStatus.SUCCESS && vitals.length === 0) {
		posture.push({
			key: 'bgp-empty',
			status: 'info',
			label: 'No routing data found for this resource',
			detail: 'not present in the BGP / RIR tables queried'
		});
	}

	return { vitals, posture, infra };
}

function shortError(msg: string): string {
	const trimmed = msg.trim();
	if (trimmed.length <= 120) return trimmed;
	return trimmed.slice(0, 117) + '…';
}

export function buildTargetSummary(target: Target, detail: TargetDetailRead | null): TargetSummary {
	if (isDomainLike(target.target_type)) return buildDomain(target, detail);
	if (isNetwork(target.target_type)) return buildNetwork(target, detail);
	return { vitals: [], posture: [], infra: [] };
}
