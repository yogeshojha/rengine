import {
	ChatState,
	type ChannelKind,
	type ChatGroup,
	type CommandSource,
	type ListenerState
} from '$lib/config/channels';
import type { McpCall, McpCapability, McpCapabilitySpec } from '$lib/types/mcp';

export interface BotInfo {
	id: string;
	username: string;
	name: string;
}

export interface ListenerStatus {
	reporting: boolean;
	running: boolean;
	last_poll_at: string | null;
	updates_seen: number;
	last_error: string | null;
	last_error_at: string | null;
}

export interface ChannelStatus {
	channel: ChannelKind;
	label: string;
	configured: boolean;
	enabled: boolean;
	started_at: string | null;
	secret_masked: string | null;
	bot: BotInfo | null;
	listener: ListenerStatus;
	rate_limit_per_minute: number;
	ceiling: Record<string, boolean>;
	capabilities: McpCapabilitySpec[];
	chats_total: number;
	chats_active: number;
	pending_total: number;
	commands_total: number;
	calls_recent: number;
	last_call_at: string | null;
}

export interface ChannelCatalogEntry {
	channel: ChannelKind;
	label: string;
	configured: boolean;
	enabled: boolean;
	running: boolean;
}

export interface ChannelSettingsUpdate {
	enabled?: boolean;
	rate_limit_per_minute?: number;
	ceiling?: Record<string, boolean>;
}

export interface ChannelVerifyResult {
	ok: boolean;
	bot: BotInfo | null;
	error: string | null;
}

export interface PairingRequest {
	code: string;
	external_id: string;
	display: string;
	username: string | null;
	first_name: string | null;
	requested_at: string;
	expires_at: string;
}

export interface PairingApprove {
	user_id: string;
	project_id: string;
	capabilities: McpCapability[];
}

export interface ChannelChat {
	id: string;
	channel: ChannelKind;
	external_id: string;
	display: string;
	user_id: string | null;
	username: string | null;
	totp_enabled: boolean;
	project_id: string | null;
	project_name: string | null;
	capabilities: string[];
	effective_capabilities: string[];
	state: ChatState;
	approved_at: string | null;
	revoked_at: string | null;
	last_seen_at: string | null;
	last_command: string | null;
	calls: number;
	created_at: string;
}

export interface ChannelChatUpdate {
	project_id?: string;
	capabilities?: string[];
}

export interface CommandArg {
	name: string;
	type: string;
	required: boolean;
	description: string;
	default: string | null;
	options: string[];
}

export interface ChannelCommand {
	name: string;
	tool: string | null;
	source: CommandSource;
	group: ChatGroup;
	title: string;
	description: string;
	capability: McpCapability;
	touches_target: boolean;
	queued: boolean;
	value_field: string;
	presets: Record<string, unknown>;
	usage: string;
	args: CommandArg[];
}

export type ChannelCall = McpCall;

export function listenerState(status: ChannelStatus | null): ListenerState {
	if (!status || !status.configured) return 'unconfigured';
	if (!status.enabled) return 'stopped';
	if (status.listener.running) return 'listening';
	return status.listener.reporting ? 'faulted' : 'unreachable';
}

export function chatUsable(chat: ChannelChat): boolean {
	return chat.state === ChatState.ACTIVE;
}

export function commandFor(tool: string, commands: ChannelCommand[]): string {
	return commands.find((c) => c.tool === tool)?.name ?? tool;
}

export function chatName(tokenName: string): string {
	const [, ...rest] = tokenName.split(':');
	return rest.length ? rest.join(':') : tokenName;
}

export function allowedKeys(status: ChannelStatus): Set<string> {
	return new Set(
		status.capabilities.filter((c) => c.always || status.ceiling[c.key]).map((c) => c.key)
	);
}
