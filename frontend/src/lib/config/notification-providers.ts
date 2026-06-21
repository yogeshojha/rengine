import type { Component } from 'svelte';
import SlackIcon from '@lucide/svelte/icons/slack';
import MessageSquareIcon from '@lucide/svelte/icons/message-square';
import SendIcon from '@lucide/svelte/icons/send';
import UsersIcon from '@lucide/svelte/icons/users';
import MailIcon from '@lucide/svelte/icons/mail';
import WebhookIcon from '@lucide/svelte/icons/webhook';
import SlidersHorizontalIcon from '@lucide/svelte/icons/sliders-horizontal';
import { MASK } from '$lib/constants';
import type { NotifProvider } from '$lib/types/notification-channel';

export type FieldKind = 'text' | 'secret' | 'number' | 'bool';

export interface FieldMeta {
	key: string;
	label: string;
	placeholder?: string;
	kind: FieldKind;
	required?: boolean;
	default?: string | number | boolean;
}

export interface ProviderMeta {
	provider: NotifProvider;
	name: string;
	icon: Component;
	fields: FieldMeta[];
	help?: { label: string; url: string };
}

export const NOTIFICATION_PROVIDERS: ProviderMeta[] = [
	{
		provider: 'slack',
		name: 'Slack',
		icon: SlackIcon,
		fields: [{ key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://hooks.slack.com/services/...', kind: 'secret', required: true }],
		help: { label: 'Create a Slack webhook', url: 'https://api.slack.com/messaging/webhooks' }
	},
	{
		provider: 'discord',
		name: 'Discord',
		icon: MessageSquareIcon,
		fields: [{ key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://discord.com/api/webhooks/...', kind: 'secret', required: true }]
	},
	{
		provider: 'telegram',
		name: 'Telegram',
		icon: SendIcon,
		fields: [
			{ key: 'bot_token', label: 'Bot token', placeholder: '123456:ABC-DEF...', kind: 'secret', required: true },
			{ key: 'chat_id', label: 'Chat ID', placeholder: '-1001234567890', kind: 'text', required: true }
		],
		help: { label: 'Create a Telegram bot', url: 'https://core.telegram.org/bots#how-do-i-create-a-bot' }
	},
	{
		provider: 'teams',
		name: 'Microsoft Teams',
		icon: UsersIcon,
		fields: [{ key: 'webhook_url', label: 'Incoming webhook URL', placeholder: 'https://...webhook.office.com/...', kind: 'secret', required: true }]
	},
	{
		provider: 'email',
		name: 'Email (SMTP)',
		icon: MailIcon,
		fields: [
			{ key: 'smtp_host', label: 'SMTP host', placeholder: 'smtp.gmail.com', kind: 'text', required: true },
			{ key: 'smtp_port', label: 'Port', placeholder: '587', kind: 'number', default: 587 },
			{ key: 'username', label: 'Username', placeholder: 'you@example.com', kind: 'text', required: true },
			{ key: 'password', label: 'Password / app password', placeholder: MASK, kind: 'secret', required: true },
			{ key: 'from_email', label: 'From address', placeholder: 'rengine@example.com', kind: 'text' },
			{ key: 'to_email', label: 'Send to', placeholder: 'soc@example.com', kind: 'text', required: true },
			{ key: 'use_tls', label: 'Use TLS', kind: 'bool', default: true }
		]
	},
	{
		provider: 'webhook',
		name: 'Webhook',
		icon: WebhookIcon,
		fields: [{ key: 'webhook_url', label: 'Endpoint URL', placeholder: 'https://example.com/hook', kind: 'secret', required: true }]
	},
	{
		provider: 'custom',
		name: 'Custom (Apprise)',
		icon: SlidersHorizontalIcon,
		fields: [{ key: 'apprise_url', label: 'Apprise URL', placeholder: 'ntfy://user:pass@ntfy.sh/topic', kind: 'secret', required: true }],
		help: { label: 'Apprise URL formats (100+ services)', url: 'https://github.com/caronc/apprise/wiki' }
	}
];

export const ONBOARDING_NOTIFICATION_PROVIDERS: ProviderMeta[] = ['slack', 'discord', 'teams', 'telegram']
	.map((p) => NOTIFICATION_PROVIDERS.find((m) => m.provider === p))
	.filter((m): m is ProviderMeta => m !== undefined);

export function notificationProviderMeta(provider: string): ProviderMeta {
	return NOTIFICATION_PROVIDERS.find((p) => p.provider === provider) ?? NOTIFICATION_PROVIDERS[0];
}
