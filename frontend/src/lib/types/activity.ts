import type { ActivityEvent } from '$lib/config/activity';
import type { MessageLevel } from '$lib/types/message-level';

export type ActivityLevel = MessageLevel;

export interface ActivityLog {
	id: string;
	timestamp: string;
	level: ActivityLevel;
	event_type: ActivityEvent;
	title: string;
	description: string | null;
	project_id: string | null;
	target_id: string | null;
	user_id: string | null;
	scan_id: string | null;
	target_value: string | null;
}

export interface ActivityDay {
	label: string;
	date: string;
	rows: ActivityLog[];
}
