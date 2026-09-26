import { describe, expect, it } from 'vitest';
import { LatestRequest } from './latest-request';

function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (err: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

describe('LatestRequest', () => {
	it('keeps a request current until a newer one starts', () => {
		const req = new LatestRequest();
		const first = req.begin();
		expect(first()).toBe(true);
		const second = req.begin();
		expect(first()).toBe(false);
		expect(second()).toBe(true);
	});

	it('retires the request in flight on cancel', () => {
		const req = new LatestRequest();
		const current = req.begin();
		req.cancel();
		expect(current()).toBe(false);
	});

	it('drops a slow answer that lands after a newer one', async () => {
		const req = new LatestRequest();
		const slow = deferred<string>();
		const fast = deferred<string>();
		const landed: string[] = [];
		const settled: string[] = [];
		const a = req.run(() => slow.promise, {
			done: (res) => landed.push(res),
			settled: () => settled.push('a')
		});
		const b = req.run(() => fast.promise, {
			done: (res) => landed.push(res),
			settled: () => settled.push('b')
		});
		fast.resolve('new');
		await b;
		slow.resolve('old');
		await a;
		expect(landed).toEqual(['new']);
		expect(settled).toEqual(['b']);
	});

	it('reports a failure only for the newest request', async () => {
		const req = new LatestRequest();
		const failed: unknown[] = [];
		const stale = deferred<string>();
		const a = req.run(() => stale.promise, { done: () => {}, failed: (e) => failed.push(e) });
		const b = req.run(() => Promise.reject(new Error('newest')), {
			done: () => {},
			failed: (e) => failed.push((e as Error).message)
		});
		await b;
		stale.reject(new Error('stale'));
		await a;
		expect(failed).toEqual(['newest']);
	});
});
