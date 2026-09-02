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
