import { ROUTES } from '$lib/config/routes';
import { SURFACE, SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
import { lex, quoteValue } from '$lib/utilities/query-lexer';
import { TargetType } from '$lib/types/target';

export const COMMAND_PREFIX = '>';

// mirrors toolbox/tools/cve.py:CVE_PATTERN
const CVE = /^CVE-\d{4}-\d{4,7}$/i;
const HEX = /^[0-9a-f]{32,64}$/i;
const NOT_A_FIELD = /is not a field/;

export const isCve = (value: string) => CVE.test(value.trim());
export const isHexHash = (value: string) => HEX.test(value.trim());
export const cveId = (value: string) => value.trim().toUpperCase();

export type ScopeKind = 'scan' | 'target' | 'project';

export interface PaletteScope {
	kind: ScopeKind;
	label: string;
	scanId: string | null;
	targetId: string | null;
	targetValue: string | null;
}

export type FieldLookup = (name: string) => boolean;

export interface QueryMatch {
	dimension: SurfaceDimension;
	fields: number;
}

/** Dimensions whose grammar compiles every field in the input, best first. */
export function queryDimensions(
	input: string,
	known: (dimension: SurfaceDimension) => FieldLookup
): QueryMatch[] {
	const source = input.trim();
	if (!source) return [];
	const matches: QueryMatch[] = [];
	for (const spec of SURFACE_ORDER) {
		const result = lex(source, known(spec.key));
		const fields = result.tokens.filter((t) => t.kind === 'field').length;
		if (!fields) continue;
		if (result.problems.some((p) => NOT_A_FIELD.test(p.message))) continue;
		matches.push({ dimension: spec.key, fields });
	}
	return matches.sort((a, b) => b.fields - a.fields);
}

/** Narrows a query to one target, for pages that carry no target scope. */
export function scopedQuery(query: string, targetValue: string | null): string {
	if (!targetValue) return query;
	const anchor = `target:${quoteValue(targetValue)}`;
	const rest = query.trim();
	return rest ? `${anchor} and (${rest})` : anchor;
}

export function searchHref(
	dimension: SurfaceDimension,
	query: string,
	scope: PaletteScope,
	where: 'here' | 'project'
): string {
	const spec = SURFACE[dimension];
	if (where === 'here' && scope.scanId) {
		return ROUTES.scanTab(scope.scanId, spec.tab, { [spec.queryParam]: query });
	}
	const value = where === 'here' ? scopedQuery(query, scope.targetValue) : query;
	return ROUTES.surface(spec.tab, value ? { [spec.queryParam]: value } : undefined);
}

export interface AssetLookup {
	dimension: SurfaceDimension;
	query: string;
}

const D = SurfaceDimension;

/** Field and dimension order a pasted value is looked up by, per target type. */
const LOOKUP: Record<TargetType, [SurfaceDimension, string][]> = {
	[TargetType.DOMAIN]: [
		[D.WEB_ASSETS, 'host'],
		[D.ENDPOINTS, 'host'],
		[D.SERVICES, 'host'],
		[D.VULNERABILITIES, 'host']
	],
	[TargetType.URL]: [
		[D.ENDPOINTS, 'url'],
		[D.WEB_ASSETS, 'url']
	],
	[TargetType.IP]: [
		[D.IPS, 'ip'],
		[D.SERVICES, 'ip'],
		[D.WEB_ASSETS, 'ip'],
		[D.VULNERABILITIES, 'ip']
	],
	[TargetType.IP_RANGE]: [
		[D.IPS, 'ip'],
		[D.SERVICES, 'ip'],
		[D.WEB_ASSETS, 'ip']
	],
	[TargetType.ASN]: [
		[D.IPS, 'asn'],
		[D.WEB_ASSETS, 'asn'],
		[D.SERVICES, 'asn']
	]
};

/** Where a pasted value can be looked up. */
export function assetLookups(value: string, type: TargetType | null): AssetLookup[] {
	if (!type) return [];
	const term = type === TargetType.ASN ? value.trim().replace(/^as/i, '') : value.trim();
	return LOOKUP[type].map(([dimension, field]) => ({
		dimension,
		query: `${field}:${quoteValue(term)}`
	}));
}

/** Where a CVE is recorded: a scanner's finding, then a version match. */
export function cveLookups(value: string): AssetLookup[] {
	const id = value.trim().toUpperCase();
	return [
		{ dimension: D.VULNERABILITIES, query: `cve:${id}` },
		{ dimension: D.SOFTWARE, query: `cve:${id}` }
	];
}

/** The two identities a 32–64 character hex value stands for. */
export function hashLookups(value: string): AssetLookup[] {
	const hash = value.trim().toLowerCase();
	return [
		{ dimension: D.WEB_ASSETS, query: `content_hash:${hash}` },
		{ dimension: D.WEB_ASSETS, query: `cert.fingerprint:${hash}` }
	];
}

export function hostOf(value: string): string | null {
	try {
		return new URL(value).hostname || null;
	} catch {
		return null;
	}
}
