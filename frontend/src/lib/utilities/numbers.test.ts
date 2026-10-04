import { describe, expect, it } from 'vitest';
import { compactCount, COMPACT_FROM_SHORT } from './numbers';

describe('compactCount', () => {
	it.each([
		[0, '0'],
		[999, '999'],
		[1000, '1,000'],
		[9999, '9,999'],
		[10_000, '10K'],
		[12_345, '12K'],
		[123_456, '123K'],
		[1_500_000, '1.5M']
	])('reads %d as %s', (n, expected) => {
		expect(compactCount(n)).toBe(expected);
	});

	it.each([
		[0, '0'],
		[999, '999'],
		[1000, '1K'],
		[1234, '1.2K'],
		[9999, '10K'],
		[10_000, '10K'],
		[1_500_000, '1.5M']
	])('with the short threshold reads %d as %s', (n, expected) => {
		expect(compactCount(n, COMPACT_FROM_SHORT)).toBe(expected);
	});

	it('writes a capital suffix', () => {
		expect(compactCount(25_000)).not.toMatch(/k/);
		expect(compactCount(2_500_000_000)).toBe('2.5B');
	});

	it('rounds a fraction below the threshold', () => {
		expect(compactCount(2.5, COMPACT_FROM_SHORT)).toBe('3');
	});

	it('abbreviates a negative count by its size', () => {
		expect(compactCount(-12_000)).toBe('-12K');
	});
});
