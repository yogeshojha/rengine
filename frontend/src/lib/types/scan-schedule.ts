export const SCHEDULE_TYPES = ['one_off', 'interval', 'daily_at', 'cron'] as const;
export type ScheduleType = (typeof SCHEDULE_TYPES)[number];

export const SCHEDULE_TYPE_BADGE: Record<ScheduleType, string> = {
	one_off: 'Once',
	interval: 'Recurring',
	daily_at: 'Daily',
	cron: 'Cron'
};

export const INTERVAL_UNITS = ['minutes', 'hours', 'days', 'weeks'] as const;
export type IntervalUnit = (typeof INTERVAL_UNITS)[number];

export const INTERVAL_UNIT_LABELS: Record<IntervalUnit, string> = {
	minutes: 'Minutes',
	hours: 'Hours',
	days: 'Days',
	weeks: 'Weeks'
};

export const SCHEDULE_STATUSES = ['active', 'paused', 'completed'] as const;
export type ScheduleStatus = (typeof SCHEDULE_STATUSES)[number];

export const SCHEDULE_STATUS_LABELS: Record<ScheduleStatus, string> = {
	active: 'Active',
	paused: 'Paused',
	completed: 'Completed'
};

export interface ScheduleTargetRef {
	id: string;
	target_value: string;
	target_type: string;
}

export interface ScanScheduleRead {
	id: string;
	project_id: string;
	name: string;
	target_ids: string[];
	targets: ScheduleTargetRef[];
	engine_id: string;
	engine_name: string;
	context_id: string | null;
	context_name: string | null;
	schedule_type: ScheduleType;
	run_at: string | null;
	interval_every: number | null;
	interval_unit: IntervalUnit | null;
	daily_at_time: string | null;
	cron_expression: string | null;
	timezone: string;
	status: ScheduleStatus;
	next_run_at: string | null;
	last_run_at: string | null;
	last_error: string | null;
	total_run_count: number;
	cadence: string;
	timezone_stale: boolean;
	created_by: string;
	created_at: string;
	updated_at: string;
}

export interface ScanScheduleCreate {
	name: string;
	target_ids: string[];
	engine_id: string;
	context_id?: string | null;
	schedule_type: ScheduleType;
	run_at?: string | null;
	interval_every?: number | null;
	interval_unit?: IntervalUnit | null;
	daily_at_time?: string | null;
	cron_expression?: string | null;
}

export type ScanScheduleUpdate = Partial<ScanScheduleCreate>;
