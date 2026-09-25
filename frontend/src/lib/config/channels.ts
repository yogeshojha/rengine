// mirrors shared/definitions/channels.py

export const REMOTE_CONTROL_POLL_MS = 10_000;

export enum ChannelKind {
	TELEGRAM = 'telegram'
}

export const CHANNEL_ORDER: ChannelKind[] = [ChannelKind.TELEGRAM];

export const CHANNEL_LABELS: Record<ChannelKind, string> = {
	[ChannelKind.TELEGRAM]: 'Telegram'
};

export enum ChatState {
	ACTIVE = 'active',
	REVOKED = 'revoked',
	BLOCKED = 'blocked'
}

export const CHAT_STATE_ORDER: ChatState[] = [
	ChatState.ACTIVE,
	ChatState.REVOKED,
	ChatState.BLOCKED
];

export const CHAT_STATE_LABELS: Record<ChatState, string> = {
	[ChatState.ACTIVE]: 'Active',
	[ChatState.REVOKED]: 'Revoked',
	[ChatState.BLOCKED]: 'Blocked'
};

export enum CommandSource {
	MCP = 'mcp',
	TOOLBOX = 'toolbox',
	BUILTIN = 'builtin'
}

export const COMMAND_SOURCE_ORDER: CommandSource[] = [
	CommandSource.BUILTIN,
	CommandSource.MCP,
	CommandSource.TOOLBOX
];

export const COMMAND_SOURCE_LABELS: Record<CommandSource, string> = {
	[CommandSource.BUILTIN]: 'Chat',
	[CommandSource.MCP]: 'Tools',
	[CommandSource.TOOLBOX]: 'Lookups'
};

export enum ChatGroup {
	TARGETS = 'targets',
	SCANS = 'scans',
	RESULTS = 'results',
	LOOKUPS = 'lookups',
	CHAT = 'chat'
}

export const CHAT_GROUP_ORDER: ChatGroup[] = [
	ChatGroup.TARGETS,
	ChatGroup.SCANS,
	ChatGroup.RESULTS,
	ChatGroup.LOOKUPS,
	ChatGroup.CHAT
];

export const CHAT_GROUP_LABELS: Record<ChatGroup, string> = {
	[ChatGroup.TARGETS]: 'Targets',
	[ChatGroup.SCANS]: 'Scans',
	[ChatGroup.RESULTS]: 'Results',
	[ChatGroup.LOOKUPS]: 'Lookups',
	[ChatGroup.CHAT]: 'Chat'
};

export const CHANNEL_VIEWS = ['chats', 'activity', 'commands'] as const;
export type ChannelView = (typeof CHANNEL_VIEWS)[number];

export const CHANNEL_VIEW_LABELS: Record<ChannelView, string> = {
	chats: 'Chats',
	activity: 'Activity',
	commands: 'Commands'
};

export type ListenerState = 'listening' | 'stopped' | 'unconfigured' | 'unreachable' | 'faulted';

export const LISTENER_STATE_LABELS: Record<ListenerState, string> = {
	listening: 'Listening',
	stopped: 'Stopped',
	unconfigured: 'No API key',
	unreachable: 'Listener down',
	faulted: 'Not connected'
};

export const LISTENER_STATE_DOT: Record<ListenerState, string> = {
	listening: 'bg-info',
	stopped: 'bg-muted-foreground/40',
	unconfigured: 'bg-muted-foreground/40',
	unreachable: 'bg-warning',
	faulted: 'bg-destructive'
};

export const TELEGRAM_BOTFATHER_URL = 'https://t.me/BotFather';
export const TELEGRAM_CHAT_URL = (username: string) => `https://t.me/${username}`;

export interface ChannelMeta {
	tokenSource: string;
	tokenSourceUrl: string;
	tokenPlaceholder: string;
	chatUrl: (username: string) => string;
}

export const CHANNEL_META: Record<ChannelKind, ChannelMeta> = {
	[ChannelKind.TELEGRAM]: {
		tokenSource: '@BotFather',
		tokenSourceUrl: TELEGRAM_BOTFATHER_URL,
		tokenPlaceholder: '123456789:AAF…',
		chatUrl: TELEGRAM_CHAT_URL
	}
};
