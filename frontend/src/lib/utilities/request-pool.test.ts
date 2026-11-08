import { describe, expect, it } from 'vitest';
import { requestPool } from './request-pool';

describe('requestPool', () => {
	it('holds tasks past the limit until one settles', async () => {
		const run = requestPool(2);
		let peak = 0;
		let live = 0;
		const task = (fail = false) =>
			run(async () => {
				live++;
				peak = Math.max(peak, live);
				await new Promise((r) => setTimeout(r, 5));
				live--;
				if (fail) throw new Error('refused');
				return live;
			});
		const results = await Promise.allSettled([task(), task(true), task(), task(), task()]);
		expect(peak).toBe(2);
		expect(results.filter((r) => r.status === 'rejected')).toHaveLength(1);
	});
});
