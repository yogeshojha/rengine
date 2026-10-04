import { describe, expect, it } from 'vitest';
import { formatMilliseconds, formatSeconds } from './format';

describe('formatMilliseconds', () => {
	it.each([
		[0, '0ms'],
		[850, '850ms'],
		[999, '999ms'],
		[999.6, '1s'],
		[1000, '1s'],
		[1200, '1.2s'],
		[9949, '9.9s'],
		[9950, '10s'],
		[45_000, '45s'],
		[59_600, '1m'],
		[120_000, '2m'],
		[192_000, '3m 12s'],
		[3_600_000, '1h'],
		[3_840_000, '1h 4m'],
		[7_260_000, '2h 1m']
	])('reads %d ms as %s', (ms, expected) => {
		expect(formatMilliseconds(ms)).toBe(expected);
	});

	it('never puts a space between the value and its unit', () => {
		for (const ms of [0, 850, 1200, 45_000]) expect(formatMilliseconds(ms)).not.toMatch(/\d /);
	});

	it('reads a missing value as empty and a negative one as zero', () => {
		expect(formatMilliseconds(null)).toBe('');
		expect(formatMilliseconds(undefined)).toBe('');
		expect(formatMilliseconds(Number.NaN)).toBe('');
		expect(formatMilliseconds(-40)).toBe('0ms');
	});
});

describe('formatSeconds', () => {
	it.each([
		[0, '0ms'],
		[0.85, '850ms'],
		[1.2, '1.2s'],
		[45, '45s'],
		[120, '2m'],
		[125, '2m 5s'],
		[192, '3m 12s'],
		[3840, '1h 4m'],
		[7200, '2h'],
		[7260, '2h 1m']
	])('reads %d s as %s', (seconds, expected) => {
		expect(formatSeconds(seconds)).toBe(expected);
	});

	it('agrees with formatMilliseconds', () => {
		for (const s of [0, 0.85, 1.2, 45, 192, 3840]) {
			expect(formatSeconds(s)).toBe(formatMilliseconds(s * 1000));
		}
	});

	it('reads a missing value as empty', () => {
		expect(formatSeconds(null)).toBe('');
		expect(formatSeconds(undefined)).toBe('');
	});
});
