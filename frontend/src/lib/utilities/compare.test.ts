import { describe, expect, it } from 'vitest';
import { eligibility } from './compare';
import { REFUSAL } from '$lib/config/compare';
import type { ScanRead } from '$lib/types/scan';

function scan(over: Partial<ScanRead> = {}): ScanRead {
	return {
		id: over.id ?? crypto.randomUUID(),
		target_id: 'target-a',
		scope: 'full',
		status: 'completed',
		started_at: '2026-09-10T10:00:00Z',
		created_at: '2026-09-10T10:00:00Z',
		...over
	} as ScanRead;
}

describe('eligibility', () => {
	it('asks for a second run when only one is selected', () => {
		expect(eligibility([scan()])).toMatchObject({
			ok: false,
			reason: REFUSAL.NEED_ONE_MORE
		});
	});

	it('refuses three runs', () => {
		expect(eligibility([scan(), scan(), scan()])).toMatchObject({
			ok: false,
			reason: REFUSAL.TOO_MANY
		});
	});

	it('refuses two targets', () => {
		const pair = [scan(), scan({ target_id: 'target-b' })];
		expect(eligibility(pair)).toMatchObject({
			ok: false,
			reason: REFUSAL.DIFFERENT_TARGET
		});
	});

	it('refuses a run that has not finished', () => {
		const pair = [scan(), scan({ status: 'running' })];
		expect(eligibility(pair)).toMatchObject({ ok: false, reason: REFUSAL.UNFINISHED });
	});

	it('refuses a focused run against a full one', () => {
		const pair = [scan({ scope: 'focused' }), scan({ scope: 'full' })];
		expect(eligibility(pair)).toMatchObject({
			ok: false,
			reason: REFUSAL.FOCUSED_AGAINST_FULL
		});
	});

	it('refuses the same run twice', () => {
		const one = scan({ id: 'same' });
		expect(eligibility([one, { ...one }])).toMatchObject({
			ok: false,
			reason: REFUSAL.SAME_RUN
		});
	});

	it('accepts two finished full runs of one target, oldest as baseline', () => {
		const older = scan({ id: 'older', started_at: '2026-09-10T08:00:00Z' });
		const newer = scan({ id: 'newer', started_at: '2026-09-10T12:00:00Z' });

		const out = eligibility([newer, older]);

		expect(out.ok).toBe(true);
		expect(out.baseline?.id).toBe('older');
		expect(out.current?.id).toBe('newer');
	});
});
