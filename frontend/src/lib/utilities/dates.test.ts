import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest';
import {
	dayHeading,
	formatDay,
	relativeTime,
	relativeTimeLong,
	untilTime,
	uptime,
	utcDaysSince
} from './dates';

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

	it('reaches years', () => {
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

	it('ends in ago', () => {
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

describe('uptime', () => {
	it.each([
		[0.5 * MIN, 'under a minute'],
		[1 * MIN, '1m'],
		[3 * HOUR, '3h'],
		[2 * DAY, '2d']
	])('reads %i minutes back as %s', (minutes, expected) => {
		expect(uptime(ago(minutes))).toBe(expected);
	});

	it('reads a missing start as empty, never "never"', () => {
		expect(uptime(null)).toBe('');
	});

	it('shares the bucket relativeTime uses', () => {
		expect(relativeTime(ago(3 * HOUR))).toBe(`${uptime(ago(3 * HOUR))} ago`);
	});
});

describe('untilTime', () => {
	it('reads a future moment in the same buckets', () => {
		expect(untilTime(ago(-5 * HOUR))).toBe('in 5h');
		expect(untilTime(ago(-2 * DAY))).toBe('in 2d');
	});

	it('reads a moment under a minute away', () => {
		expect(untilTime(new Date(NOW.getTime() + 20_000).toISOString())).toBe('in under a minute');
	});

	it('returns null once the moment has passed', () => {
		expect(untilTime(ago(35))).toBeNull();
		expect(untilTime(null)).toBeNull();
	});
});

describe('formatDay', () => {
	it('reads a calendar date in UTC', () => {
		expect(formatDay('2026-09-11')).toBe('Sep 11');
		expect(formatDay('2026-09-11', true)).toBe('Fri, Sep 11');
	});
});

describe('dayHeading', () => {
	const now = new Date(2026, 9, 3, 15, 30);

	it.each([
		[new Date(2026, 9, 3, 0, 5), 'Today'],
		[new Date(2026, 9, 3, 23, 59), 'Today'],
		[new Date(2026, 9, 2, 23, 59), 'Yesterday'],
		[new Date(2026, 9, 2, 0, 0), 'Yesterday'],
		[new Date(2026, 9, 1, 12, 0), 'Thu, Oct 1'],
		[new Date(2026, 0, 5, 12, 0), 'Mon, Jan 5'],
		[new Date(2025, 9, 3, 12, 0), 'Oct 3, 2025'],
		[new Date(2025, 11, 30, 12, 0), 'Dec 30, 2025']
	])('reads %s as %s', (date, expected) => {
		expect(dayHeading(date, now)).toBe(expected);
	});

	it('reads a bare calendar day in local time', () => {
		expect(dayHeading('2026-10-03', now)).toBe('Today');
		expect(dayHeading('2026-10-02', now)).toBe('Yesterday');
		expect(dayHeading('2026-09-28', now)).toBe('Mon, Sep 28');
	});

	it('takes a timestamp string', () => {
		expect(dayHeading(new Date(2026, 9, 2, 8).toISOString(), now)).toBe('Yesterday');
	});

	it('crosses a year boundary to yesterday', () => {
		const newYear = new Date(2026, 0, 1, 9, 0);
		expect(dayHeading(new Date(2025, 11, 31, 22, 0), newYear)).toBe('Yesterday');
		expect(dayHeading(new Date(2025, 11, 30, 22, 0), newYear)).toBe('Dec 30, 2025');
	});

	it('reads an invalid date as empty', () => {
		expect(dayHeading('not a date', now)).toBe('');
	});

	it('defaults to the current day', () => {
		expect(dayHeading(NOW)).toBe('Today');
	});
});

describe('utcDaysSince', () => {
	it('starts on the day the window starts and ends today', () => {
		const now = Date.parse('2026-10-02T02:23:00Z');
		expect(utcDaysSince('2026-09-25T02:23:00Z', now)).toEqual([
			'2026-09-25',
			'2026-09-26',
			'2026-09-27',
			'2026-09-28',
			'2026-09-29',
			'2026-09-30',
			'2026-10-01',
			'2026-10-02'
		]);
	});
});
