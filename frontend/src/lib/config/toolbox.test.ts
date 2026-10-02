import { describe, expect, it } from 'vitest';
import { isExternalHref, safeHref } from './toolbox';

describe('safeHref', () => {
	it('keeps http, https and same-origin paths', () => {
		expect(safeHref('https://example.com/poc')).toBe('https://example.com/poc');
		expect(safeHref('HTTP://example.com')).toBe('HTTP://example.com');
		expect(safeHref('/targets/1')).toBe('/targets/1');
	});

	it('drops other schemes and protocol-relative links', () => {
		expect(safeHref('javascript:alert(1)')).toBeNull();
		expect(safeHref('data:text/html,<script>')).toBeNull();
		expect(safeHref('//evil.example')).toBeNull();
		expect(safeHref(null)).toBeNull();
	});
});

describe('isExternalHref', () => {
	it('is true for http and https only', () => {
		expect(isExternalHref('https://example.com')).toBe(true);
		expect(isExternalHref('/targets')).toBe(false);
	});
});
