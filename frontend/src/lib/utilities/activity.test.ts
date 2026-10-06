import { describe, expect, it } from 'vitest';
import { ACTIVITY_EVENT, type ActivityEvent } from '$lib/config/activity';
import type { ActivityLog } from '$lib/types/activity';
import { activityLead, feedRows, groupByDay, unseenFailure } from './activity';

let seq = 0;
function log(event: ActivityEvent, at: string, extra: Partial<ActivityLog> = {}): ActivityLog {
	seq += 1;
	return {
		id: `a${seq}`,
		timestamp: at,
		level: 'info',
		event_type: event,
		title: 'title',
		description: null,
		project_id: 'p',
		target_id: 't',
		user_id: null,
		scan_id: null,
		target_value: 'gov.np',
		...extra
	};
}

const notLive = () => false;

describe('feedRows', () => {
	it('keeps the latest row of a run', () => {
		const paused = log(ACTIVITY_EVENT.SCAN_PAUSED, '2026-10-06T10:00:00Z', { scan_id: 's1' });
		const done = log(ACTIVITY_EVENT.SCAN_COMPLETED, '2026-10-06T12:00:00Z', { scan_id: 's1' });
		expect(feedRows([paused, done], notLive)).toEqual([done]);
	});

	it('drops a run that resumed', () => {
		const paused = log(ACTIVITY_EVENT.SCAN_PAUSED, '2026-10-06T10:00:00Z', { scan_id: 's1' });
		const resumed = log(ACTIVITY_EVENT.SCAN_RESUMED, '2026-10-06T11:00:00Z', { scan_id: 's1' });
		expect(feedRows([resumed, paused], notLive)).toEqual([]);
	});

	it('drops a run that is live', () => {
		const paused = log(ACTIVITY_EVENT.SCAN_PAUSED, '2026-10-06T10:00:00Z', { scan_id: 's1' });
		expect(feedRows([paused], (id) => id === 's1')).toEqual([]);
	});

	it('keeps rows that belong to no run and ignores unknown kinds', () => {
		const filed = log(ACTIVITY_EVENT.ISSUE_FILED, '2026-10-06T10:00:00Z', { target_id: null });
		const stage = log('scan.stage.completed' as ActivityEvent, '2026-10-06T11:00:00Z');
		expect(feedRows([stage, filed], notLive)).toEqual([filed]);
	});
});

describe('groupByDay', () => {
	it('splits rows by local day, newest first', () => {
		const a = log(ACTIVITY_EVENT.SCAN_COMPLETED, '2026-10-06T12:00:00', { scan_id: 'a' });
		const b = log(ACTIVITY_EVENT.SCAN_COMPLETED, '2026-10-06T09:00:00', { scan_id: 'b' });
		const c = log(ACTIVITY_EVENT.SCAN_COMPLETED, '2026-10-05T09:00:00', { scan_id: 'c' });
		const days = groupByDay([a, b, c], new Date('2026-10-06T13:00:00'));
		expect(days.map((d) => [d.label, d.rows.length])).toEqual([
			['Today', 2],
			['Yesterday', 1]
		]);
	});
});

describe('unseenFailure', () => {
	it('returns the newest failure after the mark', () => {
		const ok = log(ACTIVITY_EVENT.SCAN_COMPLETED, '2026-10-06T12:00:00Z', { scan_id: 'a' });
		const failed = log(ACTIVITY_EVENT.SCAN_FAILED, '2026-10-06T11:00:00Z', { scan_id: 'b' });
		const rows = [ok, failed];
		expect(unseenFailure(rows, Date.parse('2026-10-06T10:00:00Z'))).toBe(failed);
		expect(unseenFailure(rows, Date.parse('2026-10-06T11:30:00Z'))).toBeNull();
	});
});

describe('activityLead', () => {
	it('names the target for a run and the title for a batch', () => {
		const run = log(ACTIVITY_EVENT.SCAN_FAILED, '2026-10-06T12:00:00Z');
		const batch = log(ACTIVITY_EVENT.TARGET_BULK_IMPORTED, '2026-10-06T12:00:00Z', {
			title: '4 targets imported',
			target_value: null
		});
		expect(activityLead(run)).toBe('gov.np');
		expect(activityLead(batch)).toBe('4 targets imported');
	});
});
