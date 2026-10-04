import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { expiryLabel, inAppHref, spanLabel } from './mcp';
import type { McpToken } from '$lib/types/mcp';

describe('inAppHref', () => {
	it('keeps the path, query and fragment of a pivot', () => {
		expect(inAppHref('https://rengine.example/scans/1?tab=dns#a')).toBe('/scans/1?tab=dns#a');
		expect(inAppHref('/targets/1')).toBe('/targets/1');
	});

	it('drops a pivot that is not an in-app path', () => {
		expect(inAppHref('javascript:alert(1)')).toBeUndefined();
		expect(inAppHref('https://rengine.example//evil.example/x')).toBeUndefined();
		expect(inAppHref('//evil.example')).toBeUndefined();
		expect(inAppHref('scans/1')).toBeUndefined();
	});
});

describe('spanLabel', () => {
	it('reads a burst span in the shared duration form, one second at least', () => {
		expect(spanLabel(0)).toBe('1s');
		expect(spanLabel(850)).toBe('1s');
		expect(spanLabel(1200)).toBe('1.2s');
		expect(spanLabel(192_000)).toBe('3m 12s');
		expect(spanLabel(3_840_000)).toBe('1h 4m');
	});
});

describe('expiryLabel', () => {
	const NOW = new Date('2026-10-03T12:00:00Z');
	const token = (expires_at: string | null) =>
		({ expires_at, expired: false, revoked: false }) as McpToken;
	const later = (ms: number) => new Date(NOW.getTime() + ms).toISOString();

	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(NOW);
	});
	afterEach(() => vi.useRealTimers());

	it('reads hours left without a space before the unit', () => {
		expect(expiryLabel(token(later(5.5 * 3_600_000)))).toBe('In 5h');
		expect(expiryLabel(token(later(20 * 60_000)))).toBe('In 1h');
	});

	it('reads days left and a missing expiry', () => {
		expect(expiryLabel(token(later(3 * 86_400_000 + 60_000)))).toBe('In 3 days');
		expect(expiryLabel(token(null))).toBe('Never');
	});
});
