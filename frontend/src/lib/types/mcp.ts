export const MCP_CAPABILITIES = ['read', 'plan', 'write', 'launch'] as const;
export type McpCapability = (typeof MCP_CAPABILITIES)[number];

export const MCP_CAPABILITY_LABELS: Record<McpCapability, string> = {
	read: 'Read',
	plan: 'Plan',
	write: 'Write',
	launch: 'Launch'
};

export const TOUCHES_TARGETS: McpCapability[] = ['launch'];
export const MAX_TOKENS = 50;
export const MCP_DEFAULT_GRANTS: McpCapability[] = ['read', 'plan'];

export const MCP_EXPIRY_CHOICES: { value: number | null; label: string }[] = [
	{ value: 7, label: 'In 7 days' },
	{ value: 30, label: 'In 30 days' },
	{ value: 90, label: 'In 90 days' },
	{ value: 365, label: 'In a year' },
	{ value: null, label: 'Never' }
];

export interface McpCapabilitySpec {
	key: McpCapability;
	label: string;
	help: string;
	reach: string;
	always: boolean;
	touches_targets: boolean;
}

export interface McpClientSpec {
	key: string;
	label: string;
}

export interface McpClientSnippet extends McpClientSpec {
	where: string;
	lang: string;
	text: string;
}

export interface McpSession {
	token_id: string;
	client: string;
	last_seen: string;
}

export interface McpStatus {
	enabled: boolean;
	started_at: string | null;
	endpoint: string;
	stdio_command: string;
	protocol_version: string;
	rate_limit_per_minute: number;
	ceiling: Record<string, boolean>;
	sessions: McpSession[];
	capabilities: McpCapabilitySpec[];
	clients: McpClientSpec[];
}

export interface McpToken {
	id: string;
	name: string;
	project_id: string | null;
	project_name: string | null;
	capabilities: string[];
	token_prefix: string;
	expires_at: string | null;
	expired: boolean;
	revoked: boolean;
	last_used_at: string | null;
	last_client: string | null;
	calls: number;
	created_at: string;
	projects: number;
	targets: number;
}

export interface McpTokenCreated {
	token: McpToken;
	secret: string;
	clients: McpClientSnippet[];
}

export interface McpTokenUpdate {
	name?: string;
	project_id?: string | null;
	capabilities?: string[];
}

export interface McpTokenCreate {
	name: string;
	project_id?: string | null;
	capabilities: string[];
	expires_in_days?: number | null;
}

export interface McpTool {
	name: string;
	title: string;
	description: string;
	capability: McpCapability;
	group: string;
	destructive: boolean;
	examples: string[];
	context_tokens: number;
	schema: Record<string, unknown>;
}

export interface McpCall {
	at: string;
	token_id?: string | null;
	token_name: string;
	client: string;
	tool: string;
	ok: boolean;
	duration_ms: number;
	detail: string | null;
	command?: string | null;
	capability?: string | null;
	args?: string | null;
	summary?: string | null;
	pivot?: string | null;
	refused?: boolean;
}

export interface McpSettingsUpdate {
	enabled?: boolean;
	rate_limit_per_minute?: number;
	ceiling?: Record<string, boolean>;
}

export const SERVER_STATE_DOT: Record<'running' | 'stopped', string> = {
	running: 'bg-info',
	stopped: 'bg-muted-foreground/40'
};

export const SERVER_STATE_LABEL: Record<'running' | 'stopped', string> = {
	running: 'Server running',
	stopped: 'Server stopped'
};

export const AGENT_PRESENCE = ['connected', 'idle', 'offline', 'expired', 'revoked'] as const;
export type AgentPresence = (typeof AGENT_PRESENCE)[number];

export const AGENT_PRESENCE_LABELS: Record<AgentPresence, string> = {
	connected: 'Connected',
	idle: 'Idle',
	offline: 'Offline',
	expired: 'Key expired',
	revoked: 'Key revoked'
};

export const AGENT_PRESENCE_DOT: Record<AgentPresence, string> = {
	connected: 'bg-info',
	idle: 'bg-info/40',
	offline: 'bg-muted-foreground/40',
	expired: 'bg-muted-foreground/25',
	revoked: 'bg-muted-foreground/25'
};

export const CHANGING_CAPABILITIES: McpCapability[] = ['write', 'launch'];

export function tokenUsable(token: McpToken): boolean {
	return !token.revoked && !token.expired;
}

export function ceilingKeys(status: {
	capabilities: McpCapabilitySpec[];
	ceiling: Record<string, boolean>;
}): Set<string> {
	return new Set(
		status.capabilities.filter((c) => c.always || status.ceiling[c.key]).map((c) => c.key)
	);
}

export function ladderLevel(capabilities: readonly string[]): number {
	return MCP_CAPABILITIES.reduce((top, cap, i) => (capabilities.includes(cap) ? i : top), 0);
}

export function grantsUpTo(level: number, allowed: Set<string>): McpCapability[] {
	return MCP_CAPABILITIES.slice(0, level + 1).filter((c) => allowed.has(c));
}

export function regrant(
	level: number,
	held: readonly string[],
	allowed: Set<string>
): McpCapability[] | undefined {
	return level === ladderLevel(held) ? undefined : grantsUpTo(level, allowed);
}
