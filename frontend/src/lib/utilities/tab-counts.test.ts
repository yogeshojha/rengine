import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ALL_TAB, TabCounts, countTabs, withTab } from './tab-counts.svelte';
import type { QueryCounts } from '$lib/types/asset-query';

const counted = (counts: Record<string, number>): QueryCounts => ({
	counts,
	capped: Object.fromEntries(Object.keys(counts).map((k) => [k, false])),
	computed: true
});

describe('TabCounts', () => {
	beforeEach(() => vi.useFakeTimers());
	afterEach(() => vi.useRealTimers());

	it('loads once per filter', async () => {
		const tabs = new TabCounts(10);
		const load = vi.fn(async () => counted({ all: 3, '2xx': 2 }));
		tabs.track('a', load);
		tabs.track('a', load);
		await vi.runAllTimersAsync();
		expect(load).toHaveBeenCalledTimes(1);
		expect(tabs.counts).toEqual({ all: 3, '2xx': 2 });
	});

	it('drops an answer for a filter that was replaced', async () => {
		const tabs = new TabCounts(0);
		let release: (value: QueryCounts) => void = () => {};
		tabs.track(
			'old',
			() =>
				new Promise<QueryCounts>((resolve) => {
					release = resolve;
				})
		);
		await vi.advanceTimersByTimeAsync(0);
		tabs.track('new', async () => counted({ all: 7 }));
		await vi.runAllTimersAsync();
		release(counted({ all: 99 }));
		await vi.runAllTimersAsync();
		expect(tabs.counts).toEqual({ all: 7 });
	});

	it('shows no counts while a new filter loads', async () => {
		const tabs = new TabCounts(50);
		tabs.track('a', async () => counted({ all: 1 }));
		await vi.runAllTimersAsync();
		tabs.track('b', async () => counted({ all: 2 }));
		expect(tabs.counts).toBeNull();
		await vi.runAllTimersAsync();
		expect(tabs.counts).toEqual({ all: 2 });
	});

	it('shows no counts when the server could not count', async () => {
		const tabs = new TabCounts(0);
		tabs.track('a', async () => ({ counts: {}, capped: {}, computed: false }));
		await vi.runAllTimersAsync();
		expect(tabs.counts).toBeNull();
	});

	it('loads the same filter again after a failure', async () => {
		const tabs = new TabCounts(0);
		const load = vi
			.fn<() => Promise<QueryCounts>>()
			.mockRejectedValueOnce(new Error('offline'))
			.mockResolvedValueOnce(counted({ all: 4 }));
		tabs.track('a', load);
		await vi.runAllTimersAsync();
		tabs.track('a', load);
		await vi.runAllTimersAsync();
		expect(load).toHaveBeenCalledTimes(2);
		expect(tabs.counts).toEqual({ all: 4 });
	});

	it('cancels a pending load on clear', async () => {
		const tabs = new TabCounts(50);
		const load = vi.fn(async () => counted({ all: 1 }));
		tabs.track('a', load);
		tabs.clear();
		await vi.runAllTimersAsync();
		expect(load).not.toHaveBeenCalled();
		expect(tabs.counts).toBeNull();
	});
});

describe('withTab', () => {
	it('replaces the field and keeps the rest of the search', () => {
		expect(withTab('is:kev severity:high', 'severity', 'critical')).toBe(
			'is:kev severity:critical'
		);
		expect(withTab('severity:low is:kev', 'severity', 'high')).toBe('is:kev severity:high');
	});

	it('drops the field for the all tab', () => {
		expect(withTab('host:a.example.org state:exposed', 'state', ALL_TAB)).toBe(
			'host:a.example.org'
		);
		expect(withTab('state:public', 'state', ALL_TAB)).toBe('');
	});

	it('leaves a field that only shares the suffix', () => {
		expect(withTab('cvss_severity:x', 'severity', ALL_TAB)).toBe('cvss_severity:x');
	});
});

describe('countTabs', () => {
	it('asks once per distinct query and answers per tab', async () => {
		const load = vi.fn(async (queries: string[]) => ({
			counts: Object.fromEntries(queries.map((q) => [q, q.length])),
			capped: Object.fromEntries(queries.map((q) => [q, false])),
			computed: true
		}));
		const res = await countTabs(
			{ all: 'is:kev', also: 'is:kev', high: 'is:kev severity:high' },
			load
		);
		expect(load).toHaveBeenCalledWith(['is:kev', 'is:kev severity:high']);
		expect(res.counts).toEqual({ all: 6, also: 6, high: 20 });
	});

	it('leaves out a tab whose query did not compile', async () => {
		const res = await countTabs({ all: 'a', bad: 'b' }, async () => counted({ a: 1 }));
		expect(res.counts).toEqual({ all: 1 });
	});
});
