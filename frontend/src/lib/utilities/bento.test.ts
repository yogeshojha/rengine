import { describe, expect, it } from 'vitest';
import { packedSpans } from './bento';

const width = (cls: string, prefix: string) => {
	const hit = cls.split(' ').find((c) => c.startsWith(`${prefix}col-span-`));
	return hit ? Number(hit.split('-').pop()) : 12;
};

function rowsFill(spans: string[], prefix: string) {
	let used = 0;
	for (const cls of spans) {
		used += width(cls, prefix);
		if (used > 12) used = width(cls, prefix);
		if (used === 12) used = 0;
	}
	return used === 0;
}

describe('packedSpans', () => {
	it.each([1, 2, 3, 4, 5, 6, 7, 8])('fills every row with %i cells', (n) => {
		const spans = packedSpans(n);
		expect(spans).toHaveLength(n);
		expect(rowsFill(spans, 'xl:')).toBe(true);
		expect(rowsFill(spans, 'lg:')).toBe(true);
	});

	it('splits five cells three and two at xl', () => {
		expect(packedSpans(5).map((c) => width(c, 'xl:'))).toEqual([4, 4, 4, 6, 6]);
	});

	it('gives the wide cell half a row beside two others', () => {
		expect(packedSpans(3, 0).map((c) => width(c, 'xl:'))).toEqual([6, 3, 3]);
		expect(packedSpans(2, 0).map((c) => width(c, 'xl:'))).toEqual([8, 4]);
		expect(rowsFill(packedSpans(3, 0), 'lg:')).toBe(true);
	});
});
