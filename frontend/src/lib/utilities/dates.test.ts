import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest';
import { relativeTime, relativeTimeLong } from './dates';

const NOW = new Date('2026-09-11T12:00:00Z');
const ago = (minutes: number) => new Date(NOW.getTime() - minutes * 60_000).toISOString();

const MIN = 1;
const HOUR = 60;
const DAY = 60 * 24;
const MONTH = DAY * 30;
const YEAR = DAY * 365;

beforeEach(() => {
	vi.useFakeTimers();
	vi.setSystemTime(NOW);
});
afterEach(() => vi.useRealTimers());

describe('relativeTime', () => {
	it.each([
		[0.5 * MIN, 'just now'],
		[1 * MIN, '1m ago'],
		[59 * MIN, '59m ago'],
		[1 * HOUR, '1h ago'],
		[23 * HOUR, '23h ago'],
		[1 * DAY, '1d ago'],
		[29 * DAY, '29d ago'],
		[1 * MONTH, '1mo ago'],
		[11 * MONTH, '11mo ago'],
		[1 * YEAR, '1y ago'],
		[3 * YEAR, '3y ago']
	])('reads %i minutes back as %s', (minutes, expected) => {
		expect(relativeTime(ago(minutes))).toBe(expected);
	});

	it('reaches years, where a months-only helper said 36mo ago', () => {
		expect(relativeTime(ago(3 * YEAR))).toBe('3y ago');
	});
});

describe('relativeTimeLong', () => {
	it.each([
		[0.5 * MIN, 'just now'],
		[1 * MIN, '1 minute ago'],
		[2 * MIN, '2 minutes ago'],
		[1 * HOUR, '1 hour ago'],
		[5 * HOUR, '5 hours ago'],
		[1 * DAY, '1 day ago'],
		[1 * MONTH, '1 month ago'],
		[1 * YEAR, '1 year ago'],
		[3 * YEAR, '3 years ago']
	])('reads %i minutes back as %s', (minutes, expected) => {
		expect(relativeTimeLong(ago(minutes))).toBe(expected);
	});

	it('always says ago, because three call sites printed "used 3 hours"', () => {
		expect(relativeTimeLong(ago(3 * HOUR))).toBe('3 hours ago');
	});
});

describe('what neither helper may do', () => {
	it.each([null, undefined, '', 'not a date'])('reports %s as never', (value) => {
		expect(relativeTime(value)).toBe('never');
		expect(relativeTimeLong(value)).toBe('never');
	});

	it('never reads a missing date as the epoch', () => {
		expect(relativeTimeLong(null)).not.toContain('year');
	});

	it('reads a clock running ahead of ours as now, not a negative count', () => {
		const future = new Date(NOW.getTime() + 60 * 60_000).toISOString();
		expect(relativeTime(future)).toBe('just now');
		expect(relativeTimeLong(future)).toBe('just now');
	});

	it('takes a Date as readily as a string', () => {
		expect(relativeTime(new Date(NOW.getTime() - 2 * HOUR * 60_000))).toBe('2h ago');
	});
});

describe('the two renderings agree on the bucket', () => {
	it.each([1 * MIN, 90 * MIN, 5 * DAY, 7 * MONTH, 2 * YEAR])('at %i minutes back', (minutes) => {
		const short = relativeTime(ago(minutes));
		const long = relativeTimeLong(ago(minutes));
		expect(long.split(' ')[0]).toBe(short.match(/^\d+/)?.[0]);
	});
});
