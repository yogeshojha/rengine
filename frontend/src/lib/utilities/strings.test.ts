import { describe, expect, it } from 'vitest';
import { cappedCount, cappedPlural, getInitials, plural, pluralWord, withArticle } from './strings';

describe('plural', () => {
	it('agrees with the count', () => {
		expect(plural(1, 'finding')).toBe('1 finding');
		expect(plural(0, 'finding')).toBe('0 findings');
		expect(plural(2, 'finding')).toBe('2 findings');
	});

	it('takes an irregular plural', () => {
		expect(plural(2, 'excluded IP', 'excluded IPs')).toBe('2 excluded IPs');
	});

	it('groups thousands', () => {
		expect(plural(12000, 'web asset')).toBe('12,000 web assets');
	});
});

describe('pluralWord', () => {
	it('carries the noun without the count', () => {
		expect(pluralWord(1, 'scan')).toBe('scan');
		expect(pluralWord(3, 'scan')).toBe('scans');
	});
});

describe('withArticle', () => {
	it('picks the article from the first letter', () => {
		expect(withArticle('web asset')).toBe('a web asset');
		expect(withArticle('address')).toBe('an address');
		expect(withArticle('endpoint')).toBe('an endpoint');
	});
});

describe('getInitials', () => {
	it('takes two letters at most', () => {
		expect(getInitials('ada lovelace')).toBe('AL');
		expect(getInitials('grace brewster murray hopper')).toBe('GB');
	});
});

describe('cappedCount', () => {
	it('marks a count that stopped at its cap', () => {
		expect(cappedCount(10000, true)).toBe('10,000+');
		expect(cappedCount(143)).toBe('143');
	});
	it('keeps the plural noun on a capped one', () => {
		expect(cappedPlural(1, false, 'web asset')).toBe('1 web asset');
		expect(cappedPlural(10000, true, 'web asset')).toBe('10,000+ web assets');
	});
});
