import { describe, expect, it } from 'vitest';
import { ApiError, extractErrorMessage, isTransient, retryTransient } from './client';

const noWait = async () => {};

function failing(errors: unknown[], value = 'ok') {
	let calls = 0;
	return {
		get calls() {
			return calls;
		},
		run: async () => {
			const e = errors[calls++];
			if (e) throw e;
			return value;
		}
	};
}

describe('isTransient', () => {
	it('retries the rate limit, a server error and no answer', () => {
		expect(isTransient(new ApiError('Rate limit exceeded.', 429))).toBe(true);
		expect(isTransient(new ApiError('Bad gateway', 502))).toBe(true);
		expect(isTransient(new ApiError('Session not refreshed. Log in again.', 0))).toBe(true);
		expect(isTransient(new TypeError('Failed to fetch'))).toBe(true);
	});

	it('does not retry a refused session or a bad request', () => {
		expect(isTransient(new ApiError('Session expired. Log in again.', 401))).toBe(false);
		expect(isTransient(new ApiError('Account is inactive', 403))).toBe(false);
		expect(isTransient(new ApiError('Not found', 404))).toBe(false);
	});
});

describe('retryTransient', () => {
	it('answers once a 429 clears', async () => {
		const call = failing([new ApiError('Rate limit exceeded.', 429)]);
		await expect(retryTransient(call.run, [1, 1], noWait)).resolves.toBe('ok');
		expect(call.calls).toBe(2);
	});

	it('stops at the first 401', async () => {
		const call = failing([new ApiError('Session expired. Log in again.', 401)]);
		await expect(retryTransient(call.run, [1, 1], noWait)).rejects.toMatchObject({ status: 401 });
		expect(call.calls).toBe(1);
	});

	it('gives up after the last delay', async () => {
		const busy = new ApiError('Rate limit exceeded.', 429);
		const waited: number[] = [];
		const call = failing([busy, busy, busy]);
		await expect(
			retryTransient(call.run, [5, 10], async (ms) => void waited.push(ms))
		).rejects.toBe(busy);
		expect(call.calls).toBe(3);
		expect(waited).toEqual([5, 10]);
	});
});

describe('extractErrorMessage', () => {
	const field = (msg: string) => ({ loc: ['query', 'tag_ids', 0], msg, type: 'uuid_parsing' });

	it('names one or two failing fields in full', () => {
		expect(extractErrorMessage([field('Value error, Bad port')], 422)).toBe('Bad port');
		expect(extractErrorMessage([field('A'), field('B'), field('A')], 422)).toBe('A; B');
	});

	it('lets the first of many stand for the rest', () => {
		const detail = ['A', 'B', 'C', 'D'].map(field);
		expect(extractErrorMessage(detail, 422)).toBe('A (and 3 more)');
	});

	it('falls back to the status', () => {
		expect(extractErrorMessage(undefined, 500)).toBe('Request failed with status 500');
	});
});
