import { describe, expect, it } from 'vitest';
import { brandSegments, diffSegments } from './lookalikes';

describe('diffSegments', () => {
	it('marks the characters that differ from the apex', () => {
		expect(diffSegments('exarnple.com', 'example.com')).toEqual([
			{ text: 'exa', changed: false },
			{ text: 'rn', changed: true },
			{ text: 'ple.com', changed: false }
		]);
	});

	it('marks a homoglyph', () => {
		const out = diffSegments('ехample.com', 'example.com');
		expect(out.filter((s) => s.changed).map((s) => s.text)).toEqual(['ех']);
	});
});

describe('brandSegments', () => {
	it('marks the brand as a whole word', () => {
		expect(brandSegments('Uber: ride now', 'uber')).toEqual([
			{ text: 'Uber', changed: true },
			{ text: ': ride now', changed: false }
		]);
		expect(brandSegments('Huber Engineered Materials', 'uber')).toEqual([
			{ text: 'Huber Engineered Materials', changed: false }
		]);
	});
});
