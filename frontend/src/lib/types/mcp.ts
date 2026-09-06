export const MCP_CAPABILITIES = ['read', 'plan', 'write', 'launch'] as const;
export type McpCapability = (typeof MCP_CAPABILITIES)[number];

export const MCP_CAPABILITY_LABELS: Record<McpCapability, string> = {
	read: 'Read',
	plan: 'Plan',
	write: 'Write',
	launch: 'Launch'
};

export const ALWAYS_GRANTED: McpCapability[] = ['read'];
export const TOUCHES_TARGETS: McpCapability[] = ['launch'];

export const MCP_EXPIRY_CHOICES: { value: number | null; label: string }[] = [
	{ value: 7, label: 'In 7 days' },
	{ value: 30, label: 'In 30 days' },
	{ value: 90, label: 'In 90 days' },
	{ value: 365, label: 'In a year' },
	{ value: null, label: 'Never' }
];

export const MCP_TOOL_GROUPS = ['Orient', 'Interrogate', 'Explain', 'Act'] as const;

export interface McpCapabilitySpec {
	key: McpCapability;
	label: string;
	help: string;
	always: boolean;
	touches_targets: boolean;
}

export interface McpSession {
	token_id: string;
	token_name: string;
	client: string;
	capabilities: string[];
	first_seen: string;
	last_seen: string;
	calls: number;
	last_tool: string | null;
}

export interface McpStatus {
	enabled: boolean;
	started_at: string | null;
	endpoint: string;
	stdio_command: string;
	protocol_version: string;
	rate_limit_per_minute: number;
	ceiling: Record<string, boolean>;
	tools_total: number;
	tools_available: number;
	tokens_total: number;
	tokens_active: number;
	sessions: McpSession[];
	calls_today: number;
	last_call_at: string | null;
	capabilities: McpCapabilitySpec[];
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
}

export interface McpTokenCreated {
	token: McpToken;
	secret: string;
	client_config: string;
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
	schema: Record<string, unknown>;
}

export interface McpCall {
	at: string;
	token_name: string;
	client: string;
	tool: string;
	ok: boolean;
	duration_ms: number;
	detail: string | null;
}

export interface McpSettingsUpdate {
	enabled?: boolean;
	rate_limit_per_minute?: number;
	ceiling?: Record<string, boolean>;
}

// running is info, never success — success is reserved for a finished scan
export const MCP_STATE_DOT: Record<'running' | 'stopped', string> = {
	running: 'border-info bg-info shadow-[0_0_0_4px_color-mix(in_oklch,var(--info)_18%,transparent)]',
	stopped: 'border-muted-foreground/40 bg-muted-foreground/40'
};

export const MCP_STATE_LABEL: Record<'running' | 'stopped', string> = {
	running: 'Accepting connections',
	stopped: 'Stopped'
};

export function tokenState(token: McpToken): 'revoked' | 'expired' | 'active' {
	if (token.revoked) return 'revoked';
	if (token.expired) return 'expired';
	return 'active';
}
