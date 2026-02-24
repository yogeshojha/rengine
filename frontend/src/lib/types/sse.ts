/**
 * SSE channel and event type definitions.
 *
 * Mirrors backend shared/enums/sse.py.
 */

export const SSEChannel = {
    BROADCAST: 'broadcast',
    PROJECT: 'project',

    project: (projectId: string): string => `project:${projectId}`,
} as const;

export const SSEEventType = {
    NOTIFICATION: 'notification',
    ACTIVITY: 'activity',
    // TODO: target related scans enrichment
} as const;

export type SSEChannelType = (typeof SSEChannel)[keyof Omit<typeof SSEChannel, 'project'>];
export type SSEEventTypeType = (typeof SSEEventType)[keyof typeof SSEEventType];
