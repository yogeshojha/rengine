import { describe, expect, it } from 'vitest';
import { BRIEF_LIMIT, BRIEF_TTL_MS, briefKey, createBriefCache } from './ask';
import type { AskBrief, AskSubject } from '$lib/types/ask';

const SUBJECT: AskSubject = {
	dimension: 'vulnerabilities',
	key: 'fp-1',
	targetId: 't-1',
	scanId: 's-1',
	projectId: 'p-1',
	label: 'Check on example.com',
	briefId: 'v-1',
	state: 'open',
	reason: null
};

function brief(available = true): AskBrief {
	return {
		verdict: 'likely',
		label: 'Likely real',
		facts: [],
		available,
		off_reason: available ? null : 'AI is switched off.',
		model: null,
		starters: ['Is this exploitable?']
	};
}

function harness(answer: () => Promise<AskBrief> = () => Promise.resolve(brief())) {
	let clock = 0;
	const calls: AskSubject[] = [];
	const cache = createBriefCache(
		(subject) => {
			calls.push(subject);
			return answer();
		},
		() => clock
	);
	return { cache, calls, advance: (ms: number) => (clock += ms) };
}

describe('brief cache', () => {
	it('shares one request between identical concurrent calls', async () => {
		const { cache, calls } = harness();
		const [a, b] = [cache.get(SUBJECT), cache.get({ ...SUBJECT, label: 'other label' })];
		expect(a).toBe(b);
		await a;
		expect(calls).toHaveLength(1);
	});

	it('serves a settled brief without a second request', async () => {
		const { cache, calls } = harness();
		const first = await cache.get(SUBJECT);
		expect(cache.peek(SUBJECT)).toBe(first);
		expect(await cache.get(SUBJECT)).toBe(first);
		expect(calls).toHaveLength(1);
	});

	it('asks again when triage changes the state or the reason', async () => {
		const { cache, calls } = harness();
		await cache.get(SUBJECT);
		await cache.get({ ...SUBJECT, state: 'false_positive' });
		await cache.get({ ...SUBJECT, reason: 'Static file server' });
		expect(calls).toHaveLength(3);
		expect(briefKey(SUBJECT)).not.toBe(briefKey({ ...SUBJECT, state: 'confirmed' }));
	});

	it('asks again once the brief is older than the TTL', async () => {
		const { cache, calls, advance } = harness();
		await cache.get(SUBJECT);
		advance(BRIEF_TTL_MS);
		expect(cache.peek(SUBJECT)).toBeNull();
		await cache.get(SUBJECT);
		expect(calls).toHaveLength(2);
	});

	it('keeps neither an unavailable brief nor a failure', async () => {
		const off = harness(() => Promise.resolve(brief(false)));
		await off.cache.get(SUBJECT);
		expect(off.cache.peek(SUBJECT)).toBeNull();
		expect(off.cache.lastAvailable).toBe(false);
		await off.cache.get(SUBJECT);
		expect(off.calls).toHaveLength(2);

		const failing = harness(() => Promise.reject(new Error('Finding not found.')));
		await expect(failing.cache.get(SUBJECT)).rejects.toThrow('Finding not found.');
		await expect(failing.cache.get(SUBJECT)).rejects.toThrow();
		expect(failing.calls).toHaveLength(2);
	});

	it('drops the oldest brief past the limit and clears on logout', async () => {
		const { cache, calls } = harness();
		for (let i = 0; i <= BRIEF_LIMIT; i++) await cache.get({ ...SUBJECT, key: `fp-${i}` });
		expect(cache.peek({ ...SUBJECT, key: 'fp-0' })).toBeNull();
		expect(cache.peek({ ...SUBJECT, key: `fp-${BRIEF_LIMIT}` })).not.toBeNull();
		cache.clear();
		expect(cache.peek({ ...SUBJECT, key: `fp-${BRIEF_LIMIT}` })).toBeNull();
		expect(cache.lastAvailable).toBeNull();
		expect(calls).toHaveLength(BRIEF_LIMIT + 1);
	});
});
