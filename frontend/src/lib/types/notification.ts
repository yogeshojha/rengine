import type { MessageLevel } from '$lib/types/message-level';

export const NOTIFICATION_TYPES = [
	'scan',
	'system',
	'security',
	'vulnerability',
	'target',
	'resource',
	'integration'
] as const;

export type NotificationType = (typeof NOTIFICATION_TYPES)[number];

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
	scan: 'Scan',
	system: 'System',
	security: 'Security',
	vulnerability: 'Vulnerability',
	target: 'Target',
	resource: 'Resource',
	integration: 'Integration'
};

export type NotificationSeverity = MessageLevel;

export interface NotificationMetadata {
	url?: string;
	open_new_tab?: boolean;
	scan_id?: string;
	target_id?: string;
	action_label?: string;
}

export interface Notification {
	id: number;
	type: NotificationType;
	severity: NotificationSeverity;
	title: string;
	message: string;
	notification_metadata: NotificationMetadata;
	is_read: boolean;
	created_at: string;
	expires_at: string;
}

export interface NotificationStats {
	total: number;
	unread: number;
}
