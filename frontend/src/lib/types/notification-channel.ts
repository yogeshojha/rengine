import { DEFAULT_CHANNEL_EVENTS, DEFAULT_CHANNEL_LEVEL } from '$lib/config/notification-events';

export const NOTIF_PROVIDERS = [
	'slack',
	'discord',
	'telegram',
	'teams',
	'email',
	'webhook',
	'custom'
] as const;

export type NotifProvider = (typeof NOTIF_PROVIDERS)[number];

export interface NotificationPreference {
	types: string[];
	min_severity: string;
}

export interface NotificationChannelRead {
	id: string;
	name: string;
	provider: string;
	is_active: boolean;
	config_masked: Record<string, unknown>;
	events: NotificationPreference;
	created_at: string;
	updated_at: string;
	last_test_at: string | null;
	last_test_ok: boolean | null;
	last_test_message: string | null;
	last_sent_at: string | null;
	last_sent_ok: boolean | null;
	last_sent_message: string | null;
}

export interface NotificationChannelCreate {
	name: string;
	provider: string;
	is_active?: boolean;
	config: Record<string, unknown>;
	events?: NotificationPreference;
}

export interface NotificationChannelUpdate {
	name?: string;
	is_active?: boolean;
	config?: Record<string, unknown> | null;
	events?: NotificationPreference | null;
}

export function defaultNotificationPreference(): NotificationPreference {
	return { types: [...DEFAULT_CHANNEL_EVENTS], min_severity: DEFAULT_CHANNEL_LEVEL };
}
