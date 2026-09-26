import { describe, expect, it } from 'vitest';
import { SurfaceDimension } from '$lib/config/surface';
import { TargetType } from '$lib/types/target';
import {
	assetLookups,
	cveLookups,
	hashLookups,
	isCve,
	isHexHash,
	queryDimensions,
	scopedQuery,
	searchHref,
	type PaletteScope
} from './palette';

const FIELDS: Record<SurfaceDimension, string[]> = {
	[SurfaceDimension.WEB_ASSETS]: ['host', 'status', 'is', 'cert', 'target', 'ip', 'asn'],
	[SurfaceDimension.ENDPOINTS]: ['host', 'status', 'is', 'url', 'target', 'param'],
	[SurfaceDimension.SERVICES]: ['host', 'is', 'port', 'target', 'ip', 'asn'],
	[SurfaceDimension.IPS]: ['is', 'ip', 'target', 'asn', 'host'],
	[SurfaceDimension.VULNERABILITIES]: ['is', 'severity', 'target', 'host', 'ip'],
	[SurfaceDimension.SOFTWARE]: ['is', 'cve', 'target', 'host', 'software'],
	[SurfaceDimension.SECRETS]: ['is', 'secret', 'target', 'host']
};

const known = (dimension: SurfaceDimension) => (name: string) => FIELDS[dimension].includes(name);
const dims = (input: string) => queryDimensions(input, known).map((m) => m.dimension);

const PROJECT: PaletteScope = {
	kind: 'project',
	label: 'Acme',
	scanId: null,
	targetId: null,
	targetValue: null
};
const SCAN: PaletteScope = { ...PROJECT, kind: 'scan', scanId: 'run-1' };
const TARGET: PaletteScope = { ...PROJECT, kind: 'target', targetValue: 'acme.com' };

describe('shape detection', () => {
	it('reads a CVE identifier in either case', () => {
		expect(isCve('CVE-2021-44228')).toBe(true);
		expect(isCve('cve-2021-44228')).toBe(true);
		expect(isCve('CVE-21-4')).toBe(false);
		expect(isCve('acme.com')).toBe(false);
	});

	it('reads a hex identity only at a stored width', () => {
		expect(isHexHash('a'.repeat(64))).toBe(true);
		expect(isHexHash('a'.repeat(32))).toBe(true);
		expect(isHexHash('a'.repeat(31))).toBe(false);
		expect(isHexHash('z'.repeat(64))).toBe(false);
	});
});

describe('query routing', () => {
	it('offers only dimensions whose grammar carries every field', () => {
		expect(dims('severity:critical')).toEqual([SurfaceDimension.VULNERABILITIES]);
		expect(dims('secret:aws_access_key')).toEqual([SurfaceDimension.SECRETS]);
	});

	it('ranks a dimension by how many of its fields the query uses', () => {
		expect(dims('host:api.acme.com and status:200')[0]).toBe(SurfaceDimension.WEB_ASSETS);
	});

	it('refuses a dimension that does not know one of the fields', () => {
		expect(dims('host:api.acme.com and severity:high')).toEqual([SurfaceDimension.VULNERABILITIES]);
	});

	it('is not a query when nothing names a field', () => {
		expect(dims('acme.com')).toEqual([]);
		expect(dims('https://acme.com/login')).toEqual([]);
		expect(dims('CVE-2021-44228')).toEqual([]);
		expect(dims('')).toEqual([]);
	});
});

describe('scope', () => {
	it('narrows a query to one target', () => {
		expect(scopedQuery('is:new', 'acme.com')).toBe('target:acme.com and (is:new)');
		expect(scopedQuery('', 'acme.com')).toBe('target:acme.com');
		expect(scopedQuery('is:new', null)).toBe('is:new');
	});

	it('quotes a target value the grammar would split', () => {
		expect(scopedQuery('is:new', 'a b.com')).toBe('target:"a b.com" and (is:new)');
	});

	it('keeps a run search on that run', () => {
		expect(searchHref(SurfaceDimension.WEB_ASSETS, 'is:new', SCAN, 'here')).toBe(
			'/scans/run-1?tab=web-assets&wa_q=is%3Anew'
		);
	});

	it('anchors a target search to the target', () => {
		expect(searchHref(SurfaceDimension.WEB_ASSETS, 'is:new', TARGET, 'here')).toBe(
			'/surface/web-assets?wa_q=target%3Aacme.com+and+%28is%3Anew%29'
		);
	});

	it('leaves a project search unscoped', () => {
		expect(searchHref(SurfaceDimension.IPS, 'is:new', SCAN, 'project')).toBe(
			'/surface/ips?ip_q=is%3Anew'
		);
	});
});

describe('pasted values', () => {
	it('looks a hostname up by host, web assets first', () => {
		const found = assetLookups('api.acme.com', TargetType.DOMAIN);
		expect(found[0]).toEqual({
			dimension: SurfaceDimension.WEB_ASSETS,
			query: 'host:api.acme.com'
		});
	});

	it('drops the AS prefix a network is typed with', () => {
		expect(assetLookups('AS13335', TargetType.ASN)[0].query).toBe('asn:13335');
	});

	it('offers nothing for a value no type was read from', () => {
		expect(assetLookups('api.acme.com', null)).toEqual([]);
	});

	it('reads a CVE in the two dimensions that record one', () => {
		expect(cveLookups('cve-2021-44228')).toEqual([
			{ dimension: SurfaceDimension.VULNERABILITIES, query: 'cve:CVE-2021-44228' },
			{ dimension: SurfaceDimension.SOFTWARE, query: 'cve:CVE-2021-44228' }
		]);
	});

	it('gives a hex identity both of its meanings', () => {
		const hash = 'f'.repeat(64);
		expect(hashLookups(hash).map((l) => l.query)).toEqual([
			`content_hash:${hash}`,
			`cert.fingerprint:${hash}`
		]);
	});
});
