import Mail from '@lucide/svelte/icons/mail';
import Send from '@lucide/svelte/icons/send';
import ShieldCheck from '@lucide/svelte/icons/shield-check';
import type { IconComponent } from './icons';
import type { DomainPostureRead, DomainPostureSummary } from '$lib/types/domain-posture';
import type { HygieneSummary } from '$lib/utilities/scan-insights';

// mirrors shared/definitions/domain_posture.py
export const PostureCheck = {
	SPF_MISSING: 'spf_missing',
	SPF_ANY_SENDER: 'spf_any_sender',
	SPF_SOFT_ALL: 'spf_soft_all',
	SPF_MULTIPLE: 'spf_multiple',
	SPF_LOOKUP_LIMIT: 'spf_lookup_limit',
	DMARC_MISSING: 'dmarc_missing',
	DMARC_NONE: 'dmarc_none',
	DMARC_PARTIAL: 'dmarc_partial',
	DMARC_SUBDOMAINS_OPEN: 'dmarc_subdomains_open',
	DMARC_NO_REPORTING: 'dmarc_no_reporting',
	DKIM_NONE_PROBED: 'dkim_none_probed',
	DKIM_WEAK_KEY: 'dkim_weak_key',
	MTA_STS_MISSING: 'mta_sts_missing',
	MTA_STS_NOT_ENFORCED: 'mta_sts_not_enforced',
	TLS_RPT_MISSING: 'tls_rpt_missing',
	DNSSEC_MISSING: 'dnssec_missing',
	DNSSEC_BROKEN: 'dnssec_broken',
	CAA_MISSING: 'caa_missing'
} as const;
export type PostureCheck = (typeof PostureCheck)[keyof typeof PostureCheck];

export const PostureGroup = { SENDER: 'sender', MAIL: 'mail', ZONE: 'zone' } as const;
export type PostureGroup = (typeof PostureGroup)[keyof typeof PostureGroup];

export const PostureTone = { WARNING: 'warning', INFO: 'info' } as const;
export type PostureTone = (typeof PostureTone)[keyof typeof PostureTone];

export const POSTURE_FIELD = 'posture';
export const DKIM_MIN_BITS = 1024;
export const POSTURE_ANY = 'any';
export const POSTURE_NONE = 'none';

export const GROUP_LABELS: Record<PostureGroup, string> = {
	sender: 'Sender authentication',
	mail: 'Mail transport',
	zone: 'Zone integrity'
};

export const GROUP_ICONS: Record<PostureGroup, IconComponent> = {
	sender: Send,
	mail: Mail,
	zone: ShieldCheck
};

export const SPF_ALL_LABELS: Record<string, string> = {
	fail: '-all',
	softfail: '~all',
	neutral: '?all',
	pass: '+all',
	absent: 'no all'
};

export interface CheckSpec {
	key: PostureCheck;
	label: string;
	control: string;
	help: string;
	applies: string;
	fix: string;
	record: string;
	group: PostureGroup;
	tone: PostureTone;
}

export const CHECKS: CheckSpec[] = [
	{
		key: 'spf_missing',
		label: 'No SPF record',
		control: 'SPF',
		help: 'No TXT record beginning v=spf1 on the zone.',
		applies: 'Every zone.',
		fix: 'Publish a v=spf1 record ending in -all.',
		record: 'TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'spf_any_sender',
		label: 'SPF allows any sender',
		control: 'SPF all mechanism',
		help: 'The SPF record ends in +all.',
		applies: 'Every zone with SPF.',
		fix: 'End the record with -all.',
		record: 'TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'spf_multiple',
		label: 'More than one SPF record',
		control: 'SPF record count',
		help: 'Two or more TXT records begin v=spf1. Receivers treat this as a permanent error.',
		applies: 'Every zone with SPF.',
		fix: 'Merge them into one record.',
		record: 'TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'spf_lookup_limit',
		label: 'SPF over the lookup limit',
		control: 'SPF lookup count',
		help: 'The record and its includes need more than 10 DNS lookups. Receivers treat this as a permanent error.',
		applies: 'Every zone with SPF.',
		fix: 'Flatten includes or remove unused mechanisms.',
		record: 'TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'dmarc_missing',
		label: 'No DMARC record',
		control: 'DMARC',
		help: 'No TXT record beginning v=DMARC1 at _dmarc.',
		applies: 'Every zone.',
		fix: 'Publish v=DMARC1; p=reject; rua=mailto:<address> at _dmarc.',
		record: '_dmarc TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'dmarc_none',
		label: 'DMARC policy is none',
		control: 'DMARC policy',
		help: 'p=none. Failing mail is delivered and only reported.',
		applies: 'Every zone with DMARC.',
		fix: 'Raise p to quarantine, then reject.',
		record: '_dmarc TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'dmarc_subdomains_open',
		label: 'DMARC leaves subdomains open',
		control: 'DMARC subdomain policy',
		help: 'sp=none while p is quarantine or reject.',
		applies: 'Every zone with an enforcing DMARC policy.',
		fix: 'Remove sp or set it to reject.',
		record: '_dmarc TXT',
		group: 'sender',
		tone: 'warning'
	},
	{
		key: 'dkim_weak_key',
		label: 'DKIM key under 1024 bits',
		control: 'DKIM key size',
		help: 'An RSA key below 1024 bits.',
		applies: 'Every zone with a readable RSA DKIM key.',
		fix: 'Rotate to a 2048-bit key.',
		record: '_domainkey TXT',
		group: 'mail',
		tone: 'warning'
	},
	{
		key: 'dnssec_broken',
		label: 'DNSSEC validation fails',
		control: 'DNSSEC',
		help: 'A validating resolver answers SERVFAIL while a plain query answers.',
		applies: 'Every zone.',
		fix: "Check the DS record and the zone's signatures.",
		record: 'DS',
		group: 'zone',
		tone: 'warning'
	},
	{
		key: 'spf_soft_all',
		label: 'SPF does not fail unknown senders',
		control: 'SPF all mechanism',
		help: 'The SPF record ends in ~all or ?all, or has no all mechanism.',
		applies: 'Every zone with SPF.',
		fix: 'End the record with -all once every sender is listed.',
		record: 'TXT',
		group: 'sender',
		tone: 'info'
	},
	{
		key: 'dmarc_partial',
		label: 'DMARC applies to a share of mail',
		control: 'DMARC pct',
		help: 'pct is below 100.',
		applies: 'Every zone with an enforcing DMARC policy.',
		fix: 'Remove pct or set it to 100.',
		record: '_dmarc TXT',
		group: 'sender',
		tone: 'info'
	},
	{
		key: 'dmarc_no_reporting',
		label: 'DMARC without reporting',
		control: 'DMARC rua',
		help: 'The record names no rua address.',
		applies: 'Every zone with DMARC.',
		fix: 'Add rua=mailto:<address> to the record.',
		record: '_dmarc TXT',
		group: 'sender',
		tone: 'info'
	},
	{
		key: 'dkim_none_probed',
		label: 'No DKIM selector answered',
		control: 'DKIM',
		help: 'None of the probed selectors returned a key. Selectors outside the list are not checked.',
		applies: 'Every zone that publishes SPF.',
		fix: 'Publish the DKIM key the mail provider issued.',
		record: '_domainkey TXT',
		group: 'mail',
		tone: 'info'
	},
	{
		key: 'mta_sts_missing',
		label: 'No MTA-STS policy',
		control: 'MTA-STS',
		help: 'No TXT record at _mta-sts.',
		applies: 'Every zone that receives mail.',
		fix: 'Publish _mta-sts and serve the policy at mta-sts.<zone>.',
		record: '_mta-sts TXT',
		group: 'mail',
		tone: 'info'
	},
	{
		key: 'mta_sts_not_enforced',
		label: 'MTA-STS not enforcing',
		control: 'MTA-STS mode',
		help: 'The policy mode is testing or none, or the policy file did not load.',
		applies: 'Every zone with an MTA-STS record.',
		fix: 'Set mode: enforce in the policy file.',
		record: 'mta-sts.txt',
		group: 'mail',
		tone: 'info'
	},
	{
		key: 'tls_rpt_missing',
		label: 'No TLS reporting',
		control: 'TLS-RPT',
		help: 'No TXT record at _smtp._tls.',
		applies: 'Every zone that receives mail.',
		fix: 'Publish v=TLSRPTv1; rua=mailto:<address> at _smtp._tls.',
		record: '_smtp._tls TXT',
		group: 'mail',
		tone: 'info'
	},
	{
		key: 'dnssec_missing',
		label: 'Zone not signed',
		control: 'DNSSEC',
		help: 'No DS record at the parent and no validated answer.',
		applies: 'Every zone.',
		fix: 'Sign the zone and publish the DS record at the registrar.',
		record: 'DS',
		group: 'zone',
		tone: 'info'
	},
	{
		key: 'caa_missing',
		label: 'No CAA record',
		control: 'CAA',
		help: 'Any certificate authority may issue for the zone.',
		applies: 'Every zone.',
		fix: 'Publish CAA records naming the authorities in use.',
		record: 'CAA',
		group: 'zone',
		tone: 'info'
	}
];

export const CHECK_BY_KEY: Record<string, CheckSpec> = Object.fromEntries(
	CHECKS.map((c) => [c.key, c])
);
export const CHECK_ORDER: Record<string, number> = Object.fromEntries(
	CHECKS.map((c, i) => [c.key, i])
);
export const SPOOFABLE_KEYS: string[] = [
	'spf_missing',
	'spf_any_sender',
	'spf_lookup_limit',
	'spf_multiple',
	'dmarc_missing',
	'dmarc_none',
	'dmarc_subdomains_open'
];

export const TONE_LABEL: Record<PostureTone, string> = { warning: 'Warning', info: 'Info' };
export const TONE_DOT: Record<PostureTone, string> = { warning: 'bg-warning', info: 'bg-info' };
export const TONE_TEXT: Record<PostureTone, string> = {
	warning: 'text-warning',
	info: 'text-info'
};

export function checkLabel(key: string): string {
	if (key === POSTURE_NONE) return 'Passes every check';
	if (key === POSTURE_ANY) return 'Any check failing';
	if (key in TONE_LABEL) return `${TONE_LABEL[key as PostureTone]} checks`;
	return CHECK_BY_KEY[key]?.label ?? key;
}

export function postureQuery(value: string): string {
	return `${POSTURE_FIELD}:${value}`;
}

export function sortChecks(keys: string[]): string[] {
	return [...keys].sort(
		(a, b) => (CHECK_ORDER[a] ?? CHECKS.length) - (CHECK_ORDER[b] ?? CHECKS.length)
	);
}

export function worstTone(keys: string[]): PostureTone | null {
	if (!keys.length) return null;
	return keys.some((k) => CHECK_BY_KEY[k]?.tone === 'warning') ? 'warning' : 'info';
}

export function isSpoofable(keys: string[]): boolean {
	return keys.some((k) => SPOOFABLE_KEYS.includes(k));
}

// ---------- zone facts ----------

export type FactTone = 'good' | 'warning' | 'info' | 'muted';

export interface ZoneFact {
	key: string;
	label: string;
	value: string;
	tone: FactTone;
	hint?: string;
}

export const FACT_CHIP: Record<FactTone, string> = {
	good: 'border-success/30 bg-success/10 text-success',
	warning: 'border-warning/30 bg-warning/10 text-warning',
	info: 'border-info/25 bg-info/10 text-info',
	muted: 'border-border text-muted-foreground'
};

const SPF_TONE: Record<string, FactTone> = {
	fail: 'good',
	softfail: 'info',
	neutral: 'info',
	absent: 'info',
	pass: 'warning'
};
const DNSSEC_TONE: Record<string, FactTone> = {
	signed: 'good',
	unsigned: 'info',
	broken: 'warning',
	unknown: 'muted'
};

export function zoneFacts(z: DomainPostureRead): ZoneFact[] {
	const checked = new Set(z.posture_checked);
	const out: ZoneFact[] = [];
	out.push(
		z.spf
			? {
					key: 'spf',
					label: 'SPF',
					value: SPF_ALL_LABELS[z.spf_all ?? ''] ?? 'present',
					tone: SPF_TONE[z.spf_all ?? ''] ?? 'muted',
					hint: z.spf_lookups != null ? `${z.spf_lookups} lookups` : undefined
				}
			: { key: 'spf', label: 'SPF', value: 'none', tone: 'warning' }
	);
	if (z.dmarc_policy) {
		const enforcing = z.dmarc_policy === 'reject' || z.dmarc_policy === 'quarantine';
		out.push({
			key: 'dmarc',
			label: 'DMARC',
			value: `p=${z.dmarc_policy}`,
			tone: enforcing ? 'good' : 'warning',
			hint: z.dmarc_inherited
				? `inherited from ${z.parent}`
				: z.dmarc_subdomain_policy
					? `sp=${z.dmarc_subdomain_policy}`
					: undefined
		});
	} else out.push({ key: 'dmarc', label: 'DMARC', value: 'none', tone: 'warning' });
	if (checked.has('dkim_none_probed'))
		out.push(
			z.dkim_selectors.length
				? {
						key: 'dkim',
						label: 'DKIM',
						value:
							z.dkim_selectors.length === 1
								? z.dkim_selectors[0]
								: `${z.dkim_selectors.length} selectors`,
						tone: z.dkim_key_bits != null && z.dkim_key_bits < DKIM_MIN_BITS ? 'warning' : 'good',
						hint: z.dkim_key_bits != null ? `${z.dkim_key_bits}-bit key` : undefined
					}
				: { key: 'dkim', label: 'DKIM', value: 'not found', tone: 'info' }
		);
	if (z.null_mx) out.push({ key: 'mx', label: 'MX', value: 'null', tone: 'muted' });
	else if (checked.has('mta_sts_missing') || checked.has('mta_sts_not_enforced'))
		out.push(
			z.mta_sts
				? {
						key: 'mta_sts',
						label: 'MTA-STS',
						value: z.mta_sts_mode ?? 'published',
						tone: z.mta_sts_mode === 'enforce' ? 'good' : 'info'
					}
				: { key: 'mta_sts', label: 'MTA-STS', value: 'none', tone: 'info' }
		);
	out.push({
		key: 'dnssec',
		label: 'DNSSEC',
		value: z.dnssec,
		tone: DNSSEC_TONE[z.dnssec] ?? 'muted'
	});
	out.push(
		z.caa.length
			? { key: 'caa', label: 'CAA', value: z.caa.join(', '), tone: 'good' }
			: { key: 'caa', label: 'CAA', value: 'none', tone: 'info' }
	);
	return out;
}

// ---------- summary rows ----------

export interface PostureRow {
	spec: CheckSpec;
	failing: number;
	applicable: number;
	query: string;
}

export function postureRows(summary: DomainPostureSummary | null): PostureRow[] {
	const byKey = new Map((summary?.checks ?? []).map((c) => [c.key, c]));
	return CHECKS.map((spec) => {
		const c = byKey.get(spec.key);
		return c
			? { spec, failing: c.failing, applicable: c.applicable, query: c.query }
			: { spec, failing: 0, applicable: 0, query: postureQuery(spec.key) };
	}).filter((r) => r.failing > 0);
}

export function hostRows(summary: HygieneSummary | null): PostureRow[] {
	const byKey = new Map((summary?.checks ?? []).map((c) => [c.key, c]));
	return CHECKS.map((spec) => {
		const c = byKey.get(spec.key);
		return c
			? { spec, failing: c.failing, applicable: c.applicable, query: c.query }
			: { spec, failing: 0, applicable: 0, query: postureQuery(spec.key) };
	}).filter((r) => r.failing > 0);
}

export interface HostBreakdown {
	warnings: PostureRow[];
	infos: PostureRow[];
	evaluated: number;
	pending: number;
}

export function hostBreakdown(summary: HygieneSummary | null): HostBreakdown {
	const failing = hostRows(summary).sort((a, b) => share(b) - share(a));
	return {
		warnings: failing.filter((r) => r.spec.tone === PostureTone.WARNING),
		infos: failing.filter((r) => r.spec.tone === PostureTone.INFO),
		evaluated: summary?.evaluated ?? 0,
		pending: summary?.pending ?? 0
	};
}

export function share(row: PostureRow): number {
	return row.applicable > 0 ? (row.failing / row.applicable) * 100 : 0;
}

export function shareLabel(row: PostureRow): string {
	const p = share(row);
	return p > 0 && p < 1 ? '<1%' : `${Math.round(p)}%`;
}
