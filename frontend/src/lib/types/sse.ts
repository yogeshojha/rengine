export const SSEChannel = {
	BROADCAST: 'broadcast',
	PROJECT: 'project',

	project: (projectId: string): string => `project:${projectId}`
} as const;

export const SSEEventType = {
	NOTIFICATION: 'notification',
	ACTIVITY: 'activity'
	// TODO: target related scans enrichment
} as const;
