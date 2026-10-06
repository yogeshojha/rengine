import { ACTIVITY_EVENT, ACTIVITY_KINDS } from '$lib/config/activity';
import type { ActivityDay, ActivityLog } from '$lib/types/activity';
import { dayHeading } from '$lib/utilities/dates';

function newestFirst(a: ActivityLog, b: ActivityLog): number {
	return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
}

/** The latest row of each run that is not moving, and every other row. */
export function feedRows(items: ActivityLog[], isLive: (scanId: string) => boolean): ActivityLog[] {
	const runs = new Set<string>();
	const rows: ActivityLog[] = [];
	for (const item of [...items].sort(newestFirst)) {
		if (!(item.event_type in ACTIVITY_KINDS)) continue;
		if (item.scan_id) {
			if (runs.has(item.scan_id)) continue;
			runs.add(item.scan_id);
			if (item.event_type === ACTIVITY_EVENT.SCAN_RESUMED || isLive(item.scan_id)) continue;
		}
		rows.push(item);
	}
	return rows;
}

export function groupByDay(rows: ActivityLog[], now: Date = new Date()): ActivityDay[] {
	const days: ActivityDay[] = [];
	for (const row of rows) {
		const date = new Date(row.timestamp).toLocaleDateString('en-CA');
		const last = days.at(-1);
		if (last?.date === date) last.rows.push(row);
		else days.push({ label: dayHeading(date, now), date, rows: [row] });
	}
	return days;
}

/** The newest failure logged after the viewer last opened the panel. */
export function unseenFailure(rows: ActivityLog[], seenAt: number): ActivityLog | null {
	return (
		rows.find(
			(row) => ACTIVITY_KINDS[row.event_type].failure && new Date(row.timestamp).getTime() > seenAt
		) ?? null
	);
}

export function activityLead(row: ActivityLog): string {
	return (ACTIVITY_KINDS[row.event_type].byTarget && row.target_value) || row.title;
}
