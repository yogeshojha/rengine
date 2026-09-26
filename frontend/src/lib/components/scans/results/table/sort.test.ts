import { describe, expect, it } from 'vitest';
import {
	flipSort,
	pageParam,
	parsePageIndex,
	parseSort,
	readParam,
	sortParam,
	type SortKey
} from './sort';

const DEFAULT: SortKey = { key: 'risk', dir: -1 };

describe('sort params', () => {
	it('reads a key and direction, ascending unless desc', () => {
		expect(parseSort('host:desc', DEFAULT)).toEqual({ key: 'host', dir: -1 });
		expect(parseSort('host:asc', DEFAULT)).toEqual({ key: 'host', dir: 1 });
		expect(parseSort('host', DEFAULT)).toEqual({ key: 'host', dir: 1 });
	});

	it('falls back to a copy of the default without a key', () => {
		const sort = parseSort(null, DEFAULT);
		expect(sort).toEqual(DEFAULT);
		expect(sort).not.toBe(DEFAULT);
		expect(parseSort('', DEFAULT)).toEqual(DEFAULT);
	});

	it('writes no param for the default sort', () => {
		expect(sortParam({ key: 'risk', dir: -1 }, DEFAULT)).toBeNull();
		expect(sortParam({ key: 'risk', dir: 1 }, DEFAULT)).toBe('risk:asc');
		expect(sortParam({ key: 'host', dir: -1 }, DEFAULT)).toBe('host:desc');
	});

	it('round-trips through the URL value', () => {
		const sort: SortKey = { key: 'host', dir: -1 };
		expect(parseSort(sortParam(sort, DEFAULT), DEFAULT)).toEqual(sort);
	});

	it('flips the sorted column and starts a new one in the given direction', () => {
		expect(flipSort({ key: 'host', dir: 1 }, 'host')).toEqual({ key: 'host', dir: -1 });
		expect(flipSort({ key: 'host', dir: -1 }, 'host')).toEqual({ key: 'host', dir: 1 });
		expect(flipSort({ key: 'host', dir: -1 }, 'port')).toEqual({ key: 'port', dir: 1 });
		expect(flipSort({ key: 'host', dir: 1 }, 'port', -1)).toEqual({ key: 'port', dir: -1 });
	});
});

describe('page params', () => {
	it('maps a one-based page to a zero-based index', () => {
		expect(parsePageIndex('3')).toBe(2);
		expect(parsePageIndex(null)).toBe(0);
		expect(parsePageIndex('0')).toBe(0);
		expect(parsePageIndex('junk')).toBe(0);
	});

	it('writes no param on the first page', () => {
		expect(pageParam(0)).toBeNull();
		expect(pageParam(2)).toBe('3');
	});
});

describe('readParam', () => {
	it('prefers the current spelling and falls back to older ones', () => {
		expect(readParam(new URLSearchParams('wa_sort=a&sort=b'), 'wa_sort', 'sort')).toBe('a');
		expect(readParam(new URLSearchParams('sort=b'), 'wa_sort', 'sort')).toBe('b');
		expect(readParam(new URLSearchParams(''), 'wa_sort', 'sort')).toBeNull();
	});
});
