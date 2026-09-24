import { SCAN_STATUSES, type ScanStatus } from '$lib/types/scan';
import { ACTIONABLE_SEVERITIES } from '$lib/config/vulnerabilities';

const SCAN_QUERY_FIELDS = ['target', 'engine', 'status', 'severity', 'is'] as const;
export const SCAN_QUERY_FLAGS = ['partial', 'added'] as const;
type Flag = (typeof SCAN_QUERY_FLAGS)[number];

export interface ScanQueryToken {
	raw: string;
	field: string | null;
	value: string;
	negated: boolean;
}

export interface ParsedScanQuery {
	tokens: ScanQueryToken[];
	search: string;
	engines: string[];
	statuses: ScanStatus[];
	severities: string[];
	flags: Partial<Record<Flag, boolean>>;
	error: string | null;
}

const TOKEN = /(-?)(?:([a-z]+):)?("([^"]*)"|\S+)/gi;

function strip(value: string): string {
	return value.startsWith('"') && value.endsWith('"') ? value.slice(1, -1) : value;
}

export function tokenize(text: string): ScanQueryToken[] {
	const out: ScanQueryToken[] = [];
	for (const m of text.matchAll(TOKEN)) {
		const field = m[2]?.toLowerCase() ?? null;
		out.push({ raw: m[0], field, value: strip(m[3]), negated: m[1] === '-' && field !== null });
	}
	return out;
}

export function parseScanQuery(
	text: string,
	severities: string[] = ACTIONABLE_SEVERITIES
): ParsedScanQuery {
	const parsed: ParsedScanQuery = {
		tokens: [],
		search: '',
		engines: [],
		statuses: [],
		severities: [],
		flags: {},
		error: null
	};
	const words: string[] = [];
	for (const t of tokenize(text)) {
		parsed.tokens.push(t);
		if (t.field === null) {
			words.push(t.raw);
			continue;
		}
		const v = t.value.toLowerCase();
		switch (t.field) {
			case 'target':
				words.push(t.value);
				break;
			case 'engine':
				parsed.engines.push(t.value);
				break;
			case 'status':
				if (!(SCAN_STATUSES as readonly string[]).includes(v))
					parsed.error ??= `Unknown status ${t.value}. Values: ${SCAN_STATUSES.join(', ')}.`;
				else parsed.statuses.push(v as ScanStatus);
				break;
			case 'severity':
				if (!severities.includes(v))
					parsed.error ??= `Unknown severity ${t.value}. Values: ${severities.join(', ')}.`;
				else parsed.severities.push(v);
				break;
			case 'is':
				if (!(SCAN_QUERY_FLAGS as readonly string[]).includes(v))
					parsed.error ??= `Unknown value is:${t.value}. Values: ${SCAN_QUERY_FLAGS.join(', ')}.`;
				else parsed.flags[v as Flag] = !t.negated;
				break;
			default:
				parsed.error ??= `Unknown field ${t.field}. Fields: ${SCAN_QUERY_FIELDS.join(', ')}.`;
		}
	}
	parsed.search = words.join(' ');
	return parsed;
}

export function quote(value: string): string {
	return /\s/.test(value) ? `"${value}"` : value;
}

export function withToken(text: string, token: string): string {
	const parts = tokenize(text).map((t) => t.raw);
	return parts.includes(token) ? text : [...parts, token].join(' ');
}

export function withoutToken(text: string, token: string): string {
	return tokenize(text)
		.map((t) => t.raw)
		.filter((raw) => raw !== token)
		.join(' ');
}

export function hasToken(text: string, token: string): boolean {
	return tokenize(text).some((t) => t.raw === token);
}
