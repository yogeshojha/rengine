import Shield from '@lucide/svelte/icons/shield';
import ShieldOff from '@lucide/svelte/icons/shield-off';
import Mail from '@lucide/svelte/icons/mail';
import CalendarClock from '@lucide/svelte/icons/calendar-clock';
import CalendarPlus from '@lucide/svelte/icons/calendar-plus';
import FileX from '@lucide/svelte/icons/file-x';
import Lock from '@lucide/svelte/icons/lock';
import LockOpen from '@lucide/svelte/icons/lock-open';
import Server from '@lucide/svelte/icons/server';
import Globe from '@lucide/svelte/icons/globe';
import Radio from '@lucide/svelte/icons/radio';
import CircleX from '@lucide/svelte/icons/circle-x';
import EyeOff from '@lucide/svelte/icons/eye-off';
import BadgeCheck from '@lucide/svelte/icons/badge-check';
import LifeBuoy from '@lucide/svelte/icons/life-buoy';
import Route from '@lucide/svelte/icons/route';
import Network from '@lucide/svelte/icons/network';
import type { IconComponent } from '$lib/config/icons';
import type { Target } from '$lib/types/target';
import type { TargetDetailRead, DnsRecordRead } from '$lib/types/target-detail';
import { TargetType } from '$lib/types/target';
import { DnsRecordType } from '$lib/types/dns';
import { TaskStatus } from '$lib/types/task-status';
import { describeDomainStatus, isRedactedName } from '$lib/types/whois';
import {
	mailProvider,
	nameserverProvider,
	registrarIcon,
	spfPolicy,
	txtPurpose,
	verificationVendors
} from '$lib/config/dns-providers';
import { countryName } from '$lib/config/country-geo';
import { isPrivateIp } from '$lib/utilities/scan-correlation';
import {
	getExpirationUrgency,
	getDomainAge,
	formatShortDate,
	MS_PER_DAY
} from '$lib/utilities/dates';

export type Tone = 'neutral' | 'good' | 'warn' | 'bad';
export type EvidenceTab = 'dns' | 'whois' | 'bgp';

export interface RailRow {
	key: string;
	label: string;
	value: string;
	sub?: string;
	mono?: boolean;
	tone?: Tone;
	brand?: string | null;
	flag?: string;
	copy?: string;
}

export interface RailGroup {
	key: string;
	title: string;
	rows: RailRow[];
	link?: { label: string; tab: EvidenceTab };
	note?: { text: string; detail?: string; tone: Tone };
	pending?: boolean;
}

export type CheckStatus = 'pass' | 'warn' | 'fail' | 'info' | 'pending';

export interface Check {
	key: string;
	status: CheckStatus;
	label: string;
	detail?: string;
	count?: string;
	unit?: string;
	icon: IconComponent;
	tab?: EvidenceTab;
}

export interface TargetIntel {
	rail: RailGroup[];
	checks: Check[];
}

const YOUNG_DOMAIN_DAYS = 90;
const VALID_RIR = /^(arin|ripe|apnic|lacnic|afrinic)/i;
const PREVIEW = 1;

const isDomainLike = (t: TargetType) => t === TargetType.DOMAIN || t === TargetType.URL;
const pendingFor = (s: TaskStatus) => s === TaskStatus.PENDING || s === TaskStatus.QUERYING;

function ofType(records: DnsRecordRead[], type: string): string[] {
	return records.filter((r) => r.record_type === type).map((r) => r.value);
}

function shortError(err: string): string {
	const first = err.split('\n')[0].trim();
	return first.length > 120 ? `${first.slice(0, 117)}…` : first;
}

function plural(n: number, one: string, many: string): string {
	return `${n.toLocaleString()} ${n === 1 ? one : many}`;
}

function daysUntil(date: string): number {
	return Math.ceil((new Date(date).getTime() - Date.now()) / MS_PER_DAY);
}

function moreOf(values: string[]): string | undefined {
	const extra = values.length - PREVIEW;
	return extra > 0 ? `+${extra} more` : undefined;
}

function buildDomain(target: Target, detail: TargetDetailRead | null): TargetIntel {
	const rail: RailGroup[] = [];
	const checks: Check[] = [];

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
	const apex = target.target_value.toLowerCase();

	const a = ofType(records, DnsRecordType.A);
	const aaaa = ofType(records, DnsRecordType.AAAA);
	const cname = ofType(records, DnsRecordType.CNAME);
	const ns = ofType(records, DnsRecordType.NS);
	const mx = ofType(records, DnsRecordType.MX);
	const txt = ofType(records, DnsRecordType.TXT);
	const caa = ofType(records, DnsRecordType.CAA);
	const realRecords = records.filter((r) => r.record_type !== DnsRecordType.CDN).length;

	const resolution: RailGroup = {
		key: 'resolution',
		title: 'Resolution',
		rows: [],
		link: realRecords ? { label: plural(realRecords, 'record', 'records'), tab: 'dns' } : undefined,
		pending: pendingFor(dnsStatus)
	};
	if (a.length)
		resolution.rows.push({
			key: 'a',
			label: 'A',
			value: a[0],
			sub: moreOf(a),
			mono: true,
			copy: a[0]
		});
	if (aaaa.length)
		resolution.rows.push({
			key: 'aaaa',
			label: 'AAAA',
			value: aaaa[0],
			sub: moreOf(aaaa),
			mono: true,
			copy: aaaa[0]
		});
	if (cname.length)
		resolution.rows.push({
			key: 'cname',
			label: 'CNAME',
			value: cname[0],
			mono: true,
			copy: cname[0]
		});
	if (!a.length && !aaaa.length && !cname.length && dnsStatus === TaskStatus.SUCCESS)
		resolution.rows.push({ key: 'a', label: 'A', value: 'No address record', tone: 'warn' });
	const nsHosts = ns.length ? ns : (whois?.nameservers ?? []);
	const nsProvider = nameserverProvider(nsHosts);
	if (nsHosts.length)
		resolution.rows.push({
			key: 'ns',
			label: 'NS',
			value: nsProvider?.name ?? nsHosts[0],
			sub: nsProvider ? plural(nsHosts.length, 'nameserver', 'nameservers') : moreOf(nsHosts),
			mono: !nsProvider,
			brand: nsProvider?.icon ?? null
		});
	if (mx.length) {
		const provider = mailProvider(mx);
		const selfHosted = !provider && mx.every((h) => h.toLowerCase().endsWith(apex));
		resolution.rows.push({
			key: 'mx',
			label: 'MX',
			value: provider?.name ?? mx[0],
			sub: provider
				? plural(mx.length, 'record', 'records')
				: selfHosted
					? 'self-hosted'
					: moreOf(mx),
			mono: !provider,
			brand: provider?.icon ?? null
		});
	}
	if (dns?.cdn)
		resolution.rows.push({
			key: 'edge',
			label: 'Edge',
			value: dns.cdn_name || 'CDN detected',
			brand: dns.cdn_name || null
		});
	const spf = txt.find((v) => /^v=spf1\b/i.test(v));
	const vendors = verificationVendors(txt);
	if (spf || vendors.length) {
		const verifs = plural(vendors.length, 'verification', 'verifications');
		resolution.rows.push({
			key: 'txt',
			label: 'TXT',
			value: spf ? `SPF ${spfPolicy(spf)}` : verifs,
			sub: spf && vendors.length ? `${verifs} · ${vendors.slice(0, 4).join(', ')}` : undefined
		});
	}
	if (dnsStatus === TaskStatus.FAILED)
		resolution.note = {
			text: 'DNS lookup failed',
			detail: target.dns_error ? shortError(target.dns_error) : undefined,
			tone: 'bad'
		};
	rail.push(resolution);

	const registration: RailGroup = {
		key: 'registration',
		title: 'Registration',
		rows: [],
		link: whois ? { label: 'WHOIS', tab: 'whois' } : undefined,
		pending: pendingFor(whoisStatus)
	};
	if (whoisStatus === TaskStatus.FAILED)
		registration.note = {
			text: 'Unavailable',
			detail: target.whois_error ? shortError(target.whois_error) : 'WHOIS lookup failed',
			tone: 'warn'
		};
	if (registrarName)
		registration.rows.push({
			key: 'registrar',
			label: 'Registrar',
			value: registrarName,
			brand: registrarIcon(registrarName)
		});
	if (registrantName)
		registration.rows.push({
			key: 'registrant',
			label: 'Registrant',
			value: registrantName,
			sub: isRedactedName(registrantName) ? 'identity redacted' : undefined
		});
	if (registrationDate)
		registration.rows.push({
			key: 'registered',
			label: 'Registered',
			value: formatShortDate(registrationDate),
			sub: getDomainAge(registrationDate)
		});
	if (expirationDate) {
		const days = daysUntil(expirationDate);
		const urgency = getExpirationUrgency(expirationDate);
		registration.rows.push({
			key: 'expires',
			label: 'Expires',
			value: formatShortDate(expirationDate),
			sub: days < 0 ? `${plural(-days, 'day', 'days')} ago` : `in ${plural(days, 'day', 'days')}`,
			tone:
				urgency === 'expired'
					? 'bad'
					: urgency === 'critical' || urgency === 'warning'
						? 'warn'
						: undefined
		});
	}
	if (whois && whois.dnssec != null)
		registration.rows.push({
			key: 'dnssec',
			label: 'DNSSEC',
			value: whois.dnssec ? 'Enabled' : 'Not enabled',
			tone: whois.dnssec ? 'good' : 'warn'
		});
	const statuses = (whois?.domain_status ?? []).map(describeDomainStatus);
	const locks = statuses.filter((s) => s.tone === 'pass' && /locked/.test(s.label));
	if (whois?.domain_status?.length)
		registration.rows.push({
			key: 'locks',
			label: 'Locks',
			value: locks.length ? locks.map((l) => l.label.replace(' locked', '')).join(' · ') : 'None',
			tone: locks.length ? undefined : 'warn'
		});
	if (registration.rows.length || registration.note || registration.pending)
		rail.push(registration);

	if (pendingFor(whoisStatus))
		checks.push({
			key: 'whois',
			status: 'pending',
			label: 'Registration lookup in progress',
			icon: FileX
		});
	else if (whoisStatus === TaskStatus.FAILED)
		checks.push({
			key: 'whois',
			status: 'warn',
			label: 'Registration data unavailable',
			detail: target.whois_error ? shortError(target.whois_error) : 'WHOIS lookup failed',
			icon: FileX,
			tab: 'whois'
		});
	else if (expirationDate) {
		const days = daysUntil(expirationDate);
		const urgency = getExpirationUrgency(expirationDate);
		if (urgency === 'expired')
			checks.push({
				key: 'expiry',
				status: 'fail',
				label: 'Registration expired',
				detail: `${formatShortDate(expirationDate)}${registrarName ? ` at ${registrarName}` : ''}`,
				icon: CalendarClock,
				tab: 'whois'
			});
		else if (urgency === 'critical' || urgency === 'warning')
			checks.push({
				key: 'expiry',
				status: 'warn',
				label: 'Registration expires',
				count: String(days),
				unit: days === 1 ? 'day' : 'days',
				detail: `${formatShortDate(expirationDate)}${registrarName ? ` at ${registrarName}` : ''}`,
				icon: CalendarClock,
				tab: 'whois'
			});
		else
			checks.push({
				key: 'expiry',
				status: 'pass',
				label: 'Registration current',
				detail: `until ${formatShortDate(expirationDate)}`,
				icon: CalendarClock,
				tab: 'whois'
			});
	}

	if (whois && whois.dnssec != null)
		checks.push(
			whois.dnssec
				? { key: 'dnssec', status: 'pass', label: 'DNSSEC enabled', icon: Shield, tab: 'whois' }
				: {
						key: 'dnssec',
						status: 'warn',
						label: 'DNSSEC not enabled',
						detail: 'Responses are not signed',
						icon: ShieldOff,
						tab: 'whois'
					}
		);

	if (statuses.length) {
		const failing = statuses.find((s) => s.tone === 'fail');
		const holding = statuses.find((s) => s.tone === 'warn');
		if (failing)
			checks.push({
				key: 'status',
				status: 'fail',
				label: failing.label,
				icon: CircleX,
				tab: 'whois'
			});
		else if (holding)
			checks.push({
				key: 'status',
				status: 'warn',
				label: holding.label,
				icon: CircleX,
				tab: 'whois'
			});
		else if (locks.length)
			checks.push({
				key: 'locks',
				status: 'pass',
				label: plural(locks.length, 'registrar lock', 'registrar locks'),
				icon: Lock,
				tab: 'whois'
			});
		else
			checks.push({
				key: 'locks',
				status: 'warn',
				label: 'No registrar locks',
				detail: 'Transfer and delete are not prohibited',
				icon: LockOpen,
				tab: 'whois'
			});
	}

	if (registrantName && isRedactedName(registrantName))
		checks.push({
			key: 'privacy',
			status: 'info',
			label: 'Registrant redacted',
			detail: registrantName,
			icon: EyeOff,
			tab: 'whois'
		});

	if (registrationDate) {
		const ageDays = Math.floor((Date.now() - new Date(registrationDate).getTime()) / MS_PER_DAY);
		if (ageDays >= 0 && ageDays < YOUNG_DOMAIN_DAYS)
			checks.push({
				key: 'young',
				status: 'info',
				label: 'Recently registered',
				count: String(ageDays),
				unit: ageDays === 1 ? 'day old' : 'days old',
				icon: CalendarPlus,
				tab: 'whois'
			});
	}

	if (pendingFor(dnsStatus))
		checks.push({
			key: 'dns',
			status: 'pending',
			label: 'DNS resolution in progress',
			icon: Globe
		});
	else if (dnsStatus === TaskStatus.FAILED)
		checks.push({
			key: 'dns',
			status: 'fail',
			label: 'DNS resolution failed',
			detail: target.dns_error ? shortError(target.dns_error) : undefined,
			icon: Globe,
			tab: 'dns'
		});

	if (spf) {
		const policy = spfPolicy(spf);
		const weak = policy !== 'strict';
		checks.push({
			key: 'spf',
			status: weak ? 'warn' : 'pass',
			label: `SPF ${policy}`,
			detail: weak ? 'Sender policy permits spoofing' : undefined,
			icon: Mail,
			tab: 'dns'
		});
	} else if (dnsStatus === TaskStatus.SUCCESS && mx.length) {
		const provider = mailProvider(mx);
		checks.push({
			key: 'spf',
			status: 'warn',
			label: 'No SPF record',
			detail: `${plural(mx.length, 'MX record', 'MX records')}${provider ? ` at ${provider.name}` : ''}, no sender policy`,
			icon: Mail,
			tab: 'dns'
		});
	}

	const dmarc = txt.find((v) => /^v=DMARC1\b/i.test(v));
	if (dmarc) {
		const policy = txtPurpose(dmarc).detail ?? '';
		checks.push({
			key: 'dmarc',
			status: /p=(reject|quarantine)/.test(policy) ? 'pass' : 'warn',
			label: `DMARC ${policy}`,
			icon: Mail,
			tab: 'dns'
		});
	}

	if (dnsStatus === TaskStatus.SUCCESS && ns.length === 1)
		checks.push({
			key: 'ns',
			status: 'warn',
			label: 'Single nameserver',
			detail: 'No DNS redundancy',
			icon: Server,
			tab: 'dns'
		});

	if (caa.length)
		checks.push({
			key: 'caa',
			status: 'pass',
			label: 'CAA restricts issuance',
			detail: [...new Set(caa.map((v) => v.split(/\s+/).pop() ?? v))].join(', '),
			icon: BadgeCheck,
			tab: 'dns'
		});

	if (dns?.cdn)
		checks.push({
			key: 'cdn',
			status: 'info',
			label: `Fronted by ${dns.cdn_name || 'a CDN'}`,
			icon: Globe,
			tab: 'dns'
		});

	if (vendors.length)
		checks.push({
			key: 'verif',
			status: 'info',
			label: plural(vendors.length, 'service verification', 'service verifications'),
			detail: vendors.join(', '),
			icon: BadgeCheck,
			tab: 'dns'
		});

	return { rail, checks };
}

function buildNetwork(target: Target, detail: TargetDetailRead | null): TargetIntel {
	const rail: RailGroup[] = [];
	const checks: Check[] = [];

	const bgp = detail?.bgp ?? null;
	const whois = detail?.whois ?? null;
	const wsum = target.whois;
	const bgpStatus = target.bgp_status;
	const whoisStatus = target.whois_status;
	const t = target.target_type;
	const isPrivate = t === TargetType.IP && isPrivateIp(target.target_value);
	const as = bgp?.as_overview ?? null;
	const rir =
		[whois?.rir, as?.rir].map((x) => (x || '').trim()).find((x) => VALID_RIR.test(x)) || '';
	const neigh = bgp?.neighbours ?? [];
	const upstream = neigh.filter((n) => n.relationship === 'upstream');
	const downstream = neigh.filter((n) => n.relationship === 'downstream');
	const prefixes = bgp?.announced_prefixes ?? [];
	const registrationDate = whois?.registration_date || wsum?.registration_date || null;
	const abuse =
		whois?.abuse_email || bgp?.abuse_contacts?.find((c) => c.abuse_email)?.abuse_email || '';
	const country = whois?.country || wsum?.country || '';
	const hasRouting = !!bgp && (!!as || prefixes.length > 0 || bgp.network_info.length > 0);

	const routing: RailGroup = {
		key: 'routing',
		title: 'Routing',
		rows: [],
		link: hasRouting ? { label: 'BGP', tab: 'bgp' } : undefined,
		pending: pendingFor(bgpStatus)
	};
	let announced: boolean | null | undefined;
	if (t === TargetType.ASN) {
		const holder = as?.holder || target.bgp?.holder || whois?.registrant_name || whois?.name;
		if (holder) routing.rows.push({ key: 'holder', label: 'Holder', value: holder });
		announced = as?.announced ?? target.bgp?.announced;
		const prefixCount = prefixes.length || target.bgp?.prefix_count || 0;
		if (prefixCount) {
			const v4 = prefixes.filter((p) => p.ip_version === 4).length;
			routing.rows.push({
				key: 'prefixes',
				label: 'Prefixes',
				value: prefixCount.toLocaleString(),
				sub: prefixes.length
					? `${v4.toLocaleString()} IPv4 · ${(prefixes.length - v4).toLocaleString()} IPv6`
					: undefined
			});
		}
		const peerCount = neigh.length || target.bgp?.peer_count || 0;
		if (peerCount)
			routing.rows.push({
				key: 'peers',
				label: 'Peers',
				value: peerCount.toLocaleString(),
				sub: neigh.length
					? `${upstream.length.toLocaleString()} upstream · ${downstream.length.toLocaleString()} downstream`
					: undefined
			});
		const top = [...upstream].sort((x, y) => (y.power ?? 0) - (x.power ?? 0))[0];
		if (top)
			routing.rows.push({
				key: 'upstream',
				label: 'Upstream',
				value: `AS${top.neighbour_asn}`,
				mono: true,
				copy: `AS${top.neighbour_asn}`
			});
		if (as?.block_resource)
			routing.rows.push({
				key: 'block',
				label: 'Block',
				value: as.block_resource,
				sub: as.block_name ?? undefined,
				mono: true
			});
	} else {
		const originAsn =
			as?.asn || target.bgp?.asn || bgp?.network_info?.[0]?.asn || bgp?.prefix_overview?.[0]?.asn;
		const holder = as?.holder || target.bgp?.holder || bgp?.prefix_overview?.[0]?.holder || '';
		const prefix =
			target.bgp?.prefix ||
			bgp?.network_info?.[0]?.prefix ||
			bgp?.prefix_overview?.[0]?.prefix ||
			whois?.network_cidr ||
			wsum?.network_cidr;
		if (prefix)
			routing.rows.push({
				key: 'prefix',
				label: t === TargetType.IP_RANGE ? 'Prefix' : 'Covering',
				value: prefix,
				mono: true,
				copy: prefix
			});
		if (originAsn)
			routing.rows.push({
				key: 'asn',
				label: 'Origin AS',
				value: `AS${originAsn}`,
				sub: holder || undefined,
				mono: true,
				copy: `AS${originAsn}`
			});
		announced =
			bgp?.prefix_overview?.[0]?.is_announced ??
			target.bgp?.announced ??
			(bgp?.network_info?.[0]?.prefix ? true : undefined);
	}
	if (announced != null)
		routing.rows.push({
			key: 'announced',
			label: 'Status',
			value: announced ? 'Announced' : 'Not announced',
			tone: announced ? 'good' : 'warn'
		});
	if (rir) routing.rows.push({ key: 'rir', label: 'Registry', value: rir.toUpperCase() });
	if (country)
		routing.rows.push({
			key: 'country',
			label: 'Country',
			value: countryName(country),
			flag: country
		});
	if (isPrivate)
		routing.note = {
			text: 'Private address range',
			detail: 'Routing lookups do not apply',
			tone: 'neutral'
		};
	else if (bgpStatus === TaskStatus.FAILED)
		routing.note = { text: 'Routing lookup failed', tone: 'warn' };
	if (routing.rows.length || routing.note || routing.pending) rail.push(routing);

	const registration: RailGroup = {
		key: 'registration',
		title: 'Registration',
		rows: [],
		link: whois ? { label: 'WHOIS', tab: 'whois' } : undefined,
		pending: pendingFor(whoisStatus)
	};
	if (whois?.name)
		registration.rows.push({
			key: 'name',
			label: t === TargetType.ASN ? 'AS name' : 'Network',
			value: whois.name,
			sub: whois.assignment_type || undefined
		});
	if (whois?.registrant_name)
		registration.rows.push({
			key: 'registrant',
			label: 'Registrant',
			value: whois.registrant_name
		});
	if (registrationDate)
		registration.rows.push({
			key: 'registered',
			label: 'Registered',
			value: formatShortDate(registrationDate),
			sub: getDomainAge(registrationDate)
		});
	if (abuse)
		registration.rows.push({ key: 'abuse', label: 'Abuse', value: abuse, mono: true, copy: abuse });
	if (isPrivate)
		registration.note = {
			text: 'Private address range',
			detail: 'Registry lookups do not apply',
			tone: 'neutral'
		};
	else if (whoisStatus === TaskStatus.FAILED)
		registration.note = {
			text: 'Unavailable',
			detail: target.whois_error ? shortError(target.whois_error) : 'WHOIS lookup failed',
			tone: 'warn'
		};
	if (registration.rows.length || registration.note || registration.pending)
		rail.push(registration);

	if (isPrivate)
		checks.push({
			key: 'private',
			status: 'info',
			label: 'Private address range',
			detail: 'Registry and routing lookups do not apply',
			icon: Network
		});
	else {
		if (pendingFor(whoisStatus))
			checks.push({
				key: 'whois',
				status: 'pending',
				label: 'Registry lookup in progress',
				icon: FileX
			});
		else if (whoisStatus === TaskStatus.FAILED)
			checks.push({
				key: 'whois',
				status: 'warn',
				label: 'Registry data unavailable',
				detail: target.whois_error ? shortError(target.whois_error) : 'WHOIS lookup failed',
				icon: FileX,
				tab: 'whois'
			});
		if (pendingFor(bgpStatus))
			checks.push({
				key: 'bgp',
				status: 'pending',
				label: 'Routing lookup in progress',
				icon: Radio
			});
		else if (bgpStatus === TaskStatus.FAILED)
			checks.push({
				key: 'bgp',
				status: 'warn',
				label: 'Routing data unavailable',
				icon: Radio,
				tab: 'bgp'
			});
		else if (announced === true)
			checks.push({
				key: 'announced',
				status: 'pass',
				label: t === TargetType.ASN ? 'AS is announced' : 'Prefix is announced',
				icon: Radio,
				tab: 'bgp'
			});
		else if (announced === false)
			checks.push({
				key: 'announced',
				status: 'warn',
				label: t === TargetType.ASN ? 'AS is not announced' : 'Prefix is not announced',
				detail: 'Not visible in the global routing table',
				icon: Radio,
				tab: 'bgp'
			});
		if (t === TargetType.ASN && upstream.length === 1)
			checks.push({
				key: 'upstream',
				status: 'info',
				label: 'Single upstream provider',
				detail: `AS${upstream[0].neighbour_asn}`,
				icon: Route,
				tab: 'bgp'
			});
	}
	if (abuse)
		checks.push({
			key: 'abuse',
			status: 'info',
			label: 'Abuse contact published',
			detail: abuse,
			icon: LifeBuoy,
			tab: 'whois'
		});

	return { rail, checks };
}

export function buildTargetIntel(target: Target, detail: TargetDetailRead | null): TargetIntel {
	return isDomainLike(target.target_type)
		? buildDomain(target, detail)
		: buildNetwork(target, detail);
}
