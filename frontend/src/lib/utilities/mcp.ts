import {
	CHANGING_CAPABILITIES,
	type AgentPresence,
	type McpCall,
	type McpCapability,
	type McpSession,
	type McpToken
} from '$lib/types/mcp';
import { MS_PER_DAY } from '$lib/utilities/dates';

export const MCP_POLL_MS = 10_000;
export const CONNECT_POLL_MS = 2_000;
export const BURST_GAP_MS = 5 * 60_000;
export const SESSION_LIVE_MS = 60_000;
export const EXPIRY_WARN_DAYS = 7;
export const TRAIL_CAP = 200;

export interface ClientInfo {
	name: string;
	version: string | null;
	kind: string | null;
}

export function parseClient(raw: string | null | undefined): ClientInfo {
	const value = (raw ?? '').trim();
	const m = value.match(/^([^/\s(]+)(?:\/([^\s(]+))?\s*(?:\(([^)]*)\))?/);
	if (!m || !value) return { name: value || 'unknown', version: null, kind: null };
	return { name: m[1], version: m[2] ?? null, kind: m[3]?.trim() || null };
}

export const agentOf = (call: McpCall) => call.token_id ?? call.token_name;

export function callsOf(calls: McpCall[], token: McpToken): McpCall[] {
	return calls.filter((c) => (c.token_id ? c.token_id === token.id : c.token_name === token.name));
}

export const isChange = (call: McpCall) =>
	call.ok && CHANGING_CAPABILITIES.includes(call.capability as McpCapability);

export function presenceOf(token: McpToken, sessions: McpSession[], now: number): AgentPresence {
	if (token.revoked) return 'revoked';
	if (token.expired) return 'expired';
	const seen = sessions
		.filter((s) => s.token_id === token.id)
		.map((s) => new Date(s.last_seen).getTime());
	if (!seen.length) return 'offline';
	return now - Math.max(...seen) < SESSION_LIVE_MS ? 'connected' : 'idle';
}

export function inAppHref(pivot: string): string {
	try {
		const url = new URL(pivot);
		return `${url.pathname}${url.search}${url.hash}`;
	} catch {
		return pivot;
	}
}

export interface CallBurst {
	key: string;
	agent: string;
	token: string;
	client: string;
	caller: string;
	calls: McpCall[];
	started: string;
	ended: string;
	failed: number;
	changes: number;
	spanMs: number;
}

export function groupBursts(calls: McpCall[], gapMs = BURST_GAP_MS): CallBurst[] {
	const perAgent = new Map<string, CallBurst[]>();
	for (const call of calls) {
		const key = `${agentOf(call)}|${call.client}`;
		const list = perAgent.get(key) ?? [];
		const current = list[list.length - 1];
		const t = new Date(call.at).getTime();
		if (current && new Date(current.started).getTime() - t <= gapMs) {
			current.calls.push(call);
			current.started = call.at;
		} else {
			list.push({
				key: '',
				agent: agentOf(call),
				token: call.token_name,
				client: call.client,
				caller: call.agent || call.client,
				calls: [call],
				started: call.at,
				ended: call.at,
				failed: 0,
				changes: 0,
				spanMs: 0
			});
		}
		perAgent.set(key, list);
	}
	const out = [...perAgent.values()].flat();
	for (const burst of out) {
		burst.key = `${burst.started}|${burst.agent}|${burst.client}`;
		burst.failed = burst.calls.filter((c) => !c.ok).length;
		burst.changes = burst.calls.filter(isChange).length;
		burst.spanMs = new Date(burst.ended).getTime() - new Date(burst.started).getTime();
	}
	return out.sort((a, b) => b.ended.localeCompare(a.ended));
}

export function durationLabel(ms: number): string {
	if (ms < 1000) return `${ms} ms`;
	if (ms < 60_000) return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
	return `${Math.round(ms / 60_000)} min`;
}

export function spanLabel(ms: number): string {
	if (ms < 60_000) return `${Math.max(1, Math.round(ms / 1000))} s`;
	if (ms < 3_600_000) return `${Math.round(ms / 60_000)} min`;
	return `${(ms / 3_600_000).toFixed(1)} h`;
}

export const timeOfDay = (iso: string) =>
	new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

export const timeWithSeconds = (iso: string) =>
	new Date(iso).toLocaleTimeString('en-US', {
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
		hour12: false
	});

export function dayLabel(iso: string, now = new Date()): string {
	const d = new Date(iso);
	const today = now.toDateString();
	const yesterday = new Date(now.getTime() - MS_PER_DAY).toDateString();
	if (d.toDateString() === today) return 'Today';
	if (d.toDateString() === yesterday) return 'Yesterday';
	return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function contextLabel(tokens: number): string {
	return tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : String(tokens);
}

export type ExpiryTone = 'none' | 'soon' | 'expired';

export function expiryTone(token: McpToken): ExpiryTone {
	if (token.revoked || !token.expires_at) return 'none';
	if (token.expired) return 'expired';
	const days = (new Date(token.expires_at).getTime() - Date.now()) / MS_PER_DAY;
	return days <= EXPIRY_WARN_DAYS ? 'soon' : 'none';
}

export function expiryLabel(token: McpToken): string {
	if (!token.expires_at) return 'Never';
	const diff = new Date(token.expires_at).getTime() - Date.now();
	if (diff <= 0) return 'Expired';
	const days = Math.floor(diff / MS_PER_DAY);
	if (days < 1) return `In ${Math.max(1, Math.floor(diff / 3_600_000))} h`;
	if (days <= EXPIRY_WARN_DAYS) return `In ${days} day${days === 1 ? '' : 's'}`;
	return new Date(token.expires_at).toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric'
	});
}

export interface ArgSpec {
	name: string;
	required: boolean;
	type: string;
	description: string;
	fallback: string | null;
	options: string[];
}

type JsonSchema = Record<string, unknown>;

function typeOf(prop: JsonSchema): string {
	if (Array.isArray(prop.enum)) return 'enum';
	if (Array.isArray(prop.anyOf)) {
		const kinds = (prop.anyOf as JsonSchema[]).map(typeOf).filter((k) => k !== 'null');
		return [...new Set(kinds)].join(' | ') || 'any';
	}
	if (prop.type === 'array') {
		const items = (prop.items ?? {}) as JsonSchema;
		return `${typeOf(items)}[]`;
	}
	if (typeof prop.type === 'string') return prop.type;
	return 'any';
}

function optionsOf(prop: JsonSchema): string[] {
	if (Array.isArray(prop.enum)) return prop.enum.map(String);
	if (Array.isArray(prop.anyOf)) {
		for (const p of prop.anyOf as JsonSchema[])
			if (Array.isArray(p.enum)) return p.enum.map(String);
	}
	if (prop.type === 'array') return optionsOf((prop.items ?? {}) as JsonSchema);
	return [];
}

export function schemaArgs(schema: Record<string, unknown>): ArgSpec[] {
	const properties = (schema.properties ?? {}) as Record<string, JsonSchema>;
	const required = new Set((schema.required ?? []) as string[]);
	return Object.entries(properties).map(([name, prop]) => ({
		name,
		required: required.has(name),
		type: typeOf(prop),
		description: typeof prop.description === 'string' ? prop.description : '',
		fallback:
			prop.default === undefined || prop.default === null ? null : JSON.stringify(prop.default),
		options: optionsOf(prop)
	}));
}
