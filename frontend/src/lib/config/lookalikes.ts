import { Severity } from '$lib/config/vulnerabilities';

export const SIMILAR_AT = 40;

export enum Verdict {
	SIMILAR_PAGE = 'similar_page',
	MAIL = 'mail',
	LIVE = 'live',
	PARKED = 'parked',
	REGISTERED = 'registered',
	LINKED = 'linked'
}

export interface VerdictSpec {
	key: Verdict;
	label: string;
	help: string;
	severity: Severity;
}

export const VERDICTS: VerdictSpec[] = [
	{
		key: Verdict.SIMILAR_PAGE,
		label: 'Similar page',
		help: `Page similarity to the target's page at or above ${SIMILAR_AT}%.`,
		severity: Severity.CRITICAL
	},
	{
		key: Verdict.MAIL,
		label: 'MX configured',
		help: 'Publishes an MX record.',
		severity: Severity.HIGH
	},
	{
		key: Verdict.LIVE,
		label: 'Web content',
		help: 'Answers HTTP with a 2xx or 3xx status.',
		severity: Severity.MEDIUM
	},
	{
		key: Verdict.PARKED,
		label: 'Parked',
		help: 'Parking nameservers, a parking page or a domain marketplace.',
		severity: Severity.LOW
	},
	{
		key: Verdict.REGISTERED,
		label: 'Registered',
		help: 'Resolves or has nameservers. No 2xx or 3xx HTTP answer.',
		severity: Severity.LOW
	},
	{
		key: Verdict.LINKED,
		label: 'Linked to target',
		help: 'Redirects to the target, shares its nameservers or is a project target.',
		severity: Severity.INFO
	}
];

export const VERDICT_BY_KEY: Record<string, VerdictSpec> = Object.fromEntries(
	VERDICTS.map((v) => [v.key, v])
);

export const THREAT_VERDICTS: ReadonlySet<string> = new Set([
	Verdict.SIMILAR_PAGE,
	Verdict.MAIL,
	Verdict.LIVE
]);

export enum LinkReason {
	REDIRECT = 'redirect',
	NAMESERVERS = 'nameservers',
	TARGET = 'target'
}

export const LINK_LABELS: Record<string, string> = {
	[LinkReason.REDIRECT]: 'Redirects to the target',
	[LinkReason.NAMESERVERS]: 'Same nameservers as the target',
	[LinkReason.TARGET]: 'Project target'
};

export enum LookalikeState {
	OPEN = 'open',
	REVIEWED = 'reviewed',
	IGNORED = 'ignored'
}

export const STATE_LABELS: Record<string, string> = {
	[LookalikeState.OPEN]: 'Open',
	[LookalikeState.REVIEWED]: 'Reviewed',
	[LookalikeState.IGNORED]: 'Ignored'
};

export const TECHNIQUE_LABELS: Record<string, string> = {
	addition: 'Added letter',
	bitsquatting: 'Bit flip',
	cyrillic: 'Cyrillic',
	homoglyph: 'Homoglyph',
	hyphenation: 'Hyphen',
	insertion: 'Inserted key',
	omission: 'Missing letter',
	plural: 'Plural',
	repetition: 'Repeated letter',
	replacement: 'Adjacent key',
	subdomain: 'Dot inserted',
	transposition: 'Swapped letters',
	'vowel-swap': 'Vowel swap',
	various: 'Common typo',
	dictionary: 'Added word',
	'tld-swap': 'Other TLD'
};

export const techniqueLabel = (key: string): string => TECHNIQUE_LABELS[key] ?? key;

export interface Segment {
	text: string;
	changed: boolean;
}

export function diffSegments(value: string, original: string): Segment[] {
	const a = Array.from(value);
	const b = Array.from(original);
	const dp: number[][] = Array.from({ length: a.length + 1 }, () =>
		new Array<number>(b.length + 1).fill(0)
	);
	for (let i = a.length - 1; i >= 0; i--)
		for (let j = b.length - 1; j >= 0; j--)
			dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
	const kept = new Array<boolean>(a.length).fill(false);
	let i = 0;
	let j = 0;
	while (i < a.length && j < b.length) {
		if (a[i] === b[j]) {
			kept[i] = true;
			i++;
			j++;
		} else if (dp[i + 1][j] >= dp[i][j + 1]) i++;
		else j++;
	}
	const out: Segment[] = [];
	a.forEach((ch, k) => {
		const changed = !kept[k];
		const last = out[out.length - 1];
		if (last && last.changed === changed) last.text += ch;
		else out.push({ text: ch, changed });
	});
	return out;
}

const MIN_BRAND = 3;

export function brandOf(apex: string): string | null {
	const label = apex.split('.')[0] ?? '';
	return label.length >= MIN_BRAND ? label : null;
}

export function brandSegments(text: string, brand: string | null): Segment[] {
	if (!brand) return [{ text, changed: false }];
	const escaped = brand.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	const parts = text.split(new RegExp(`(\\b${escaped}\\b)`, 'i'));
	return parts
		.filter((p) => p !== '')
		.map((p) => ({ text: p, changed: p.toLowerCase() === brand.toLowerCase() }));
}
