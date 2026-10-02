import { describe, expect, it } from 'vitest';
import { noteAssetHref, noteHref, noteSubject } from './subject';
import { withPicks } from './facets';
import { SurfaceDimension } from '$lib/config/surface';
import { splitHostPort } from '$lib/utilities/net';
import type { Note } from '$lib/types/note';

function note(over: Partial<Note> = {}): Note {
	return {
		id: 'n-1',
		project_id: 'p-1',
		target_id: 't-1',
		target_value: 'example.com',
		scan_id: 's-1',
		dimension: null,
		asset_key: null,
		asset_label: null,
		title: null,
		body: 'x',
		status: 'open',
		tags: [],
		triage_state: null,
		created_by: 'u-1',
		author: 'yogesh',
		created_at: '2026-10-02T00:00:00Z',
		updated_at: '2026-10-02T00:00:00Z',
		scan_at: '2026-09-12T00:00:00Z',
		finding_id: null,
		...over
	};
}

const params = (href: string | null) => new URL(href ?? '', 'http://x').searchParams;

describe('note links', () => {
	it('opens a web asset and an address on their sheets', () => {
		const web = note({ dimension: SurfaceDimension.WEB_ASSETS, asset_key: 'api.example.com' });
		expect(noteAssetHref(web)).toBe('/scans/s-1?tab=web-assets&asset=api.example.com');
		const ip = note({ dimension: SurfaceDimension.IPS, asset_key: '10.0.0.1', scan_id: null });
		expect(noteAssetHref(ip)).toBe('/surface/ips?ip=10.0.0.1');
	});

	it('opens a finding by its row in the scan, and nothing without one', () => {
		const finding = note({ dimension: SurfaceDimension.VULNERABILITIES, asset_key: 'fp' });
		expect(noteAssetHref(finding)).toBeNull();
		expect(params(noteAssetHref({ ...finding, finding_id: 'v-9' })).get('vuln')).toBe('v-9');
	});

	it('narrows endpoints, services and secrets with exact tokens', () => {
		const endpoint = note({
			dimension: SurfaceDimension.ENDPOINTS,
			asset_key: 'sig',
			asset_label: 'https://api.example.com/v2/users?id=1'
		});
		const ep = params(noteAssetHref(endpoint));
		expect(ep.get('ep_q')).toBe('url="https://api.example.com/v2/users?id=1"');
		expect(ep.get('ep_view')).toBe('list');

		const v6 = note({ dimension: SurfaceDimension.SERVICES, asset_key: '[2001:db8::1]:8443' });
		expect(params(noteAssetHref(v6)).get('svc_q')).toBe('ip="2001:db8::1" port=8443');
		const v4 = note({ dimension: SurfaceDimension.SERVICES, asset_key: '10.0.0.1:22' });
		expect(params(noteAssetHref(v4)).get('svc_q')).toBe('ip=10.0.0.1 port=22');

		const secret = note({ dimension: SurfaceDimension.SECRETS, asset_key: 'abc' });
		expect(params(noteAssetHref(secret)).get('sec_q')).toBe('fingerprint=abc');
		expect(
			noteAssetHref(note({ dimension: SurfaceDimension.SOFTWARE, asset_key: 'f' }))
		).toBeNull();
	});

	it('lands a note with no asset on its scan or its target', () => {
		expect(noteHref(note())).toBe('/scans/s-1');
		expect(noteHref(note({ scan_id: null }))).toBe('/targets/t-1');
		expect(noteSubject(note({ scan_id: null })).type).toBe('Target');
		expect(
			noteSubject(note({ dimension: SurfaceDimension.VULNERABILITIES, asset_key: 'f' })).type
		).toBe('Finding');
	});

	it('splits an authority the way the server does', () => {
		expect(splitHostPort('[2001:db8::1]:443')).toEqual(['2001:db8::1', '443']);
		expect(splitHostPort('[2001:db8::1]')).toEqual(['2001:db8::1', null]);
		expect(splitHostPort('example.com:80')).toEqual(['example.com', '80']);
		expect(splitHostPort('2001:db8::1')).toEqual(['2001:db8::1', null]);
		expect(splitHostPort('example.com')).toEqual(['example.com', null]);
	});
});

describe('facet picks', () => {
	it('keeps a pick listed at zero once the counts leave it out', () => {
		const shown = withPicks([{ value: 'b', label: 'B', count: 3 }], ['a', 'b'], (value) =>
			value === 'a' ? { value: 'a', label: 'A', count: 9 } : undefined
		);
		expect(shown).toEqual([
			{ value: 'a', label: 'A', count: 0 },
			{ value: 'b', label: 'B', count: 3 }
		]);
	});
});
