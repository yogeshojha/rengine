import { describe, expect, it } from 'vitest';
import { hasToken, parseScanQuery, withToken, withoutToken } from './scan-query';

describe('parseScanQuery', () => {
	it('splits tokens from free text', () => {
		const q = parseScanQuery(
			'acme target:shop severity:critical status:failed engine:"Full recon" is:partial -is:added'
		);
		expect(q.error).toBeNull();
		expect(q.search).toBe('acme shop');
		expect(q.severities).toEqual(['critical']);
		expect(q.statuses).toEqual(['failed']);
		expect(q.engines).toEqual(['Full recon']);
		expect(q.flags).toEqual({ partial: true, added: false });
	});

	it('refuses severities outside the shown set', () => {
		expect(parseScanQuery('severity:low').error).toBe(
			'Unknown severity low. Values: critical, high, medium.'
		);
		expect(parseScanQuery('severity:medium', ['critical', 'high']).error).toContain(
			'Unknown severity'
		);
	});

	it('names an unknown field and value', () => {
		expect(parseScanQuery('kev:true').error).toContain('Unknown field kev');
		expect(parseScanQuery('is:kev').error).toContain('Unknown value is:kev');
		expect(parseScanQuery('status:done').error).toContain('Unknown status done');
	});
});

describe('token helpers', () => {
	it('adds and removes a token once', () => {
		const a = withToken('acme', 'severity:critical');
		expect(a).toBe('acme severity:critical');
		expect(withToken(a, 'severity:critical')).toBe(a);
		expect(hasToken(a, 'severity:critical')).toBe(true);
		expect(withoutToken(a, 'severity:critical')).toBe('acme');
	});
});
