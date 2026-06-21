import type { MessageLevel } from '$lib/types/message-level';

export type NotificationType =
	| 'scan'
	| 'system'
	| 'security'
	| 'vulnerability'
	| 'target'
	| 'resource'
	| 'integration';

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
