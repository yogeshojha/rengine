import { describe, expect, it } from 'vitest';
import { bucketsSince } from './dashboard';

describe('bucketsSince', () => {
	it('keeps the calendar days the sliding window touches', () => {
		const days = ['2026-09-24', '2026-09-25', '2026-09-26'].map((date) => ({ date }));
		expect(bucketsSince(days, '2026-09-25T02:23:00Z').map((d) => d.date)).toEqual([
			'2026-09-25',
			'2026-09-26'
		]);
	});
});
