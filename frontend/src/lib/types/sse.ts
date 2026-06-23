export const SSEChannel = {
	BROADCAST: 'broadcast',
	PROJECT: 'project',
	SCAN: 'scan',

	project: (projectId: string): string => `project:${projectId}`,
	scan: (scanId: string): string => `scan:${scanId}`
} as const;

export const SSEEventType = {
	NOTIFICATION: 'notification',
	ACTIVITY: 'activity',
	SCAN: 'scan'
} as const;

export const ScanEventKind = {
	SCAN_STARTED: 'scan_started',
	SCAN_COMPLETED: 'scan_completed',
	SCAN_FAILED: 'scan_failed',
	SCAN_CANCELLED: 'scan_cancelled',
	STAGE_STARTED: 'stage_started',
	STAGE_PROGRESS: 'stage_progress',
	STAGE_COMPLETED: 'stage_completed',
	COMMAND_STARTED: 'command_started',
	COMMAND_FINISHED: 'command_finished'
} as const;

export interface ScanEvent {
	kind: string;
	scan_id: string;
	activity_id?: string | null;
	stage?: string;
	status?: string;
	engine?: string;
	title?: string;
	message?: string;
	source?: string | null;
	counts?: Record<string, number>;
	duration_seconds?: number | null;
	error?: string | null;
	command_id?: string | null;
	tool?: string;
	command?: string;
	return_code?: number;
	[key: string]: unknown;
}
