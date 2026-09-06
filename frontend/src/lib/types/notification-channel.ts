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

export const NOTIF_CATEGORIES = [
	{ value: 'scan', label: 'Scans', hint: 'Started, completed, failed' },
	{ value: 'vulnerability', label: 'Vulnerabilities', hint: 'New findings by severity' },
	{ value: 'target', label: 'Targets and assets', hint: 'Imports, new assets and endpoints' },
	{ value: 'security', label: 'Security alerts', hint: 'Logins, account changes' },
	{ value: 'system', label: 'System', hint: 'Updates and platform health' },
	{ value: 'integration', label: 'Integrations', hint: 'API key and webhook failures' },
	{ value: 'resource', label: 'Resources', hint: 'Storage and quota limits' }
] as const;

export const NOTIF_SEVERITIES = [
	{ value: 'info', label: 'Info and above' },
	{ value: 'warning', label: 'Warning and above' },
	{ value: 'error', label: 'Errors only' }
] as const;

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
	return {
		types: ['scan', 'vulnerability', 'target', 'security', 'system'],
		min_severity: 'info'
	};
}
