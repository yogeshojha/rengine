import { describe, expect, it } from 'vitest';
import { aboutRow, blockHref, groupQuery, rowHref, rowLabel } from './block-columns';
import { MAX_QUERY_LENGTH } from '$lib/config/surface';

describe('block links', () => {
	it('opens the dimension page with the block query', () => {
		const href = blockHref('web_assets', 'tech:wordpress', null);
		expect(href).toBe('/surface/web-assets?q=tech%3Awordpress');
	});

	it('narrows to the thread scope when it is filtered', () => {
		const href = blockHref('vulnerabilities', 'is:kev', ['a.com', 'b.com']) ?? '';
		const params = new URL(href, 'http://x').searchParams;
		expect(params.get('vuln_q')).toBe('target=[a.com,b.com] and (is:kev)');
		expect(params.get('vuln_view')).toBe('findings');
	});

	it('draws no link for an empty scope or an over-long query', () => {
		expect(blockHref('web_assets', 'is:new', [])).toBeNull();
		expect(blockHref('web_assets', `tech:${'x'.repeat(MAX_QUERY_LENGTH)}`, null)).toBeNull();
		expect(blockHref('web_assets', 'is:new', [], 'scan-1')).toBeNull();
	});

	it('opens a scan thread on the scan tab without a target clause', () => {
		const href = blockHref('web_assets', 'is:new', ['a.com'], 'scan-1') ?? '';
		expect(href).toContain('/scans/scan-1');
		expect(href).not.toContain('target');
	});

	it('combines a group with its block query', () => {
		expect(groupQuery('tech:x or tech:y', 'status:200')).toBe('(tech:x or tech:y) and status:200');
		expect(groupQuery(null, 'status:200')).toBe('status:200');
	});

	it('opens a row in the scan that recorded it', () => {
		const href = rowHref('web_assets', { name: 'wiki.example.com', _scan_id: 's1' }) ?? '';
		expect(href).toContain('/scans/s1');
		expect(href).toContain('asset=wiki.example.com');
	});

	it('names a service with a bracketed IPv6 address', () => {
		const row = { ip: '2001:db8::1', port: 443 };
		expect(rowLabel('services', row)).toBe('[2001:db8::1]:443');
		expect(aboutRow('services', row)).toBe('services:[2001:db8::1]:443');
	});
});
