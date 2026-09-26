import { describe, expect, it } from 'vitest';
import type { QueryGroups } from '$lib/types/asset-query';
import { GroupedView, LatestLoad } from './results-state.svelte';

function groupsFor(dimension: string): QueryGroups {
	return {
		dimension,
		groups: [],
		total_groups: 0,
		truncated: false,
		rows: 0,
		covered: 0
	} as unknown as QueryGroups;
}

function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (err: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

describe('LatestLoad', () => {
	it('keeps the newest answer when an older one lands late', async () => {
		const slot = new LatestLoad<string>();
		const slow = deferred<string>();
		const a = slot.load(() => slow.promise);
		const b = slot.load(() => Promise.resolve('new'));
		await b;
		expect(slot.value).toBe('new');
		expect(slot.loading).toBe(false);
		slow.resolve('old');
		await a;
		expect(slot.value).toBe('new');
	});

	it('marks a failure and empties the slot', async () => {
		const slot = new LatestLoad<string>();
		await slot.load(() => Promise.resolve('first'));
		await slot.load(() => Promise.reject(new Error('down')));
		expect(slot.value).toBeNull();
		expect(slot.failed).toBe(true);
		await slot.load(() => Promise.resolve('back'));
		expect(slot.failed).toBe(false);
	});

	it('shows a retry after a failure as loading, not failed', async () => {
		const slot = new LatestLoad<string>();
		await slot.load(() => Promise.reject(new Error('down')));
		const retry = deferred<string>();
		const pending = slot.load(() => retry.promise);
		expect(slot.loading).toBe(true);
		expect(slot.failed).toBe(false);
		retry.resolve('back');
		await pending;
		expect(slot.value).toBe('back');
	});
});

describe('GroupedView', () => {
	it('loads the buckets for the dimension picked', async () => {
		const asked: string[] = [];
		const view = new GroupedView(
			'status',
			(by) => {
				asked.push(by);
				return Promise.resolve(groupsFor(by));
			},
			() => true
		);
		await view.reload();
		expect(asked).toEqual(['status']);
		expect(view.value?.dimension).toBe('status');
	});

	it('drops the set without a dimension or before the table is ready', async () => {
		let ready = true;
		const view = new GroupedView(
			'status',
			(by) => Promise.resolve(groupsFor(by)),
			() => ready
		);
		await view.reload();
		view.by = '';
		await view.reload();
		expect(view.value).toBeNull();
		view.by = 'status';
		ready = false;
		await view.reload();
		expect(view.value).toBeNull();
	});

	it('keeps the newest dimension when the older answer lands late', async () => {
		const pending = new Map<string, ReturnType<typeof deferred<QueryGroups>>>();
		const view = new GroupedView(
			'status',
			(by) => {
				const d = deferred<QueryGroups>();
				pending.set(by, d);
				return d.promise;
			},
			() => true
		);
		const a = view.reload();
		view.by = 'tech';
		const b = view.reload();
		pending.get('tech')!.resolve(groupsFor('tech'));
		await b;
		pending.get('status')!.resolve(groupsFor('status'));
		await a;
		expect(view.value?.dimension).toBe('tech');
	});
});
