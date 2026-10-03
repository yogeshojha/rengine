import { afterEach, describe, expect, it, vi } from 'vitest';
import { externalHref, isExternalHref, localPath, openExternal, safeHref } from './links';

const HOSTILE = [
	'javascript:alert(1)',
	'JavaScript:alert(1)',
	' javascript:alert(1)',
	'java\tscript:alert(1)',
	'data:text/html,<script>alert(1)</script>',
	'vbscript:msgbox(1)',
	'//evil.example',
	'/\\evil.example',
	'file:///etc/passwd',
	''
];

describe('externalHref', () => {
	it('keeps http and https URLs', () => {
		expect(externalHref('https://example.com/poc?a=1')).toBe('https://example.com/poc?a=1');
		expect(externalHref('HTTP://example.com')).toBe('HTTP://example.com');
	});

	it('drops every other scheme, paths and empty values', () => {
		for (const value of [...HOSTILE, '/targets/1', null, undefined])
			expect(externalHref(value)).toBeUndefined();
	});
});

describe('safeHref', () => {
	it('keeps http, https and same-origin paths', () => {
		expect(safeHref('https://example.com/poc')).toBe('https://example.com/poc');
		expect(safeHref('/targets/1?tab=dns#a')).toBe('/targets/1?tab=dns#a');
	});

	it('drops other schemes and protocol-relative links', () => {
		for (const value of [...HOSTILE, null, undefined]) expect(safeHref(value)).toBeUndefined();
	});
});

describe('localPath', () => {
	it('keeps same-origin paths', () => {
		expect(localPath('/scans/1?tab=endpoints#a')).toBe('/scans/1?tab=endpoints#a');
	});

	it('drops absolute URLs, other schemes and protocol-relative links', () => {
		for (const value of [...HOSTILE, 'https://example.com/poc', null, undefined])
			expect(localPath(value)).toBeUndefined();
	});
});

describe('isExternalHref', () => {
	it('is true for http and https only', () => {
		expect(isExternalHref('https://example.com')).toBe(true);
		expect(isExternalHref('/targets')).toBe(false);
		expect(isExternalHref('https:example.com')).toBe(false);
	});
});

describe('openExternal', () => {
	const open = vi.fn();

	afterEach(() => {
		open.mockReset();
		vi.unstubAllGlobals();
	});

	it('opens an http URL without an opener or a referrer', () => {
		vi.stubGlobal('window', { open });
		openExternal('https://example.com/a');
		expect(open).toHaveBeenCalledWith('https://example.com/a', '_blank', 'noopener,noreferrer');
	});

	it('opens nothing for another scheme', () => {
		vi.stubGlobal('window', { open });
		for (const value of [...HOSTILE, null]) openExternal(value);
		expect(open).not.toHaveBeenCalled();
	});
});
