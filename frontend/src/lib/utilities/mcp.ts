import type { McpCall, McpSession, McpToken } from '$lib/types/mcp';
import { MS_PER_DAY } from '$lib/utilities/dates';

export const MCP_POLL_MS = 10_000;
export const BURST_GAP_MS = 5 * 60_000;
export const SESSION_LIVE_MS = 60_000;
export const PULSE_HOURS = 24;
export const EXPIRY_WARN_DAYS = 7;
export const TRAIL_CAP = 200;

export const agentKey = (client: string, token: string) => `${client}|${token}`;

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

export interface ToolTally {
	name: string;
	count: number;
}

export interface CallBurst {
	key: string;
	token: string;
	client: string;
	calls: McpCall[];
	started: string;
	ended: string;
	failed: number;
	tools: ToolTally[];
	spanMs: number;
}

export function groupBursts(calls: McpCall[], gapMs = BURST_GAP_MS): CallBurst[] {
	const perAgent = new Map<string, CallBurst[]>();
	for (const call of calls) {
		const key = agentKey(call.client, call.token_name);
		const list = perAgent.get(key) ?? [];
		const current = list[list.length - 1];
		const t = new Date(call.at).getTime();
		if (current && new Date(current.started).getTime() - t <= gapMs) {
			current.calls.push(call);
			current.started = call.at;
		} else {
			list.push({
				key: '',
				token: call.token_name,
				client: call.client,
				calls: [call],
				started: call.at,
				ended: call.at,
				failed: 0,
				tools: [],
				spanMs: 0
			});
		}
		perAgent.set(key, list);
	}
	const out = [...perAgent.values()].flat();
	for (const burst of out) {
		burst.key = `${burst.started}|${burst.token}|${burst.client}`;
		burst.failed = burst.calls.filter((c) => !c.ok).length;
		burst.tools = tally(burst.calls);
		burst.spanMs = new Date(burst.ended).getTime() - new Date(burst.started).getTime();
	}
	return out.sort((a, b) => b.ended.localeCompare(a.ended));
}

export function trailStart(calls: McpCall[], cap = TRAIL_CAP): string | null {
	return calls.length >= cap ? (calls[calls.length - 1]?.at ?? null) : null;
}

export function tally(calls: McpCall[]): ToolTally[] {
	const counts = new Map<string, number>();
	for (const c of calls) counts.set(c.tool, (counts.get(c.tool) ?? 0) + 1);
	return [...counts.entries()]
		.map(([name, count]) => ({ name, count }))
		.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

export interface PulseBucket {
	start: number;
	calls: number;
	failed: number;
}

export function hourlyPulse(
	calls: McpCall[],
	now = Date.now(),
	hours = PULSE_HOURS
): PulseBucket[] {
	const hour = 3_600_000;
	const top = new Date(now);
	top.setMinutes(0, 0, 0);
	const end = top.getTime() + hour;
	const buckets: PulseBucket[] = Array.from({ length: hours }, (_, i) => ({
		start: end - (hours - i) * hour,
		calls: 0,
		failed: 0
	}));
	const first = buckets[0].start;
	for (const c of calls) {
		const t = new Date(c.at).getTime();
		if (t < first || t >= end) continue;
		const b = buckets[Math.floor((t - first) / hour)];
		b.calls += 1;
		if (!c.ok) b.failed += 1;
	}
	return buckets;
}

export function median(values: number[]): number | null {
	if (!values.length) return null;
	const sorted = [...values].sort((a, b) => a - b);
	const mid = Math.floor(sorted.length / 2);
	return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
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

export function countByTool(calls: McpCall[]): Map<string, number> {
	const out = new Map<string, number>();
	for (const c of calls) out.set(c.tool, (out.get(c.tool) ?? 0) + 1);
	return out;
}

export interface AgentTally {
	key: string;
	client: string;
	token: string;
	count: number;
}

export function tallyAgents(calls: McpCall[]): AgentTally[] {
	const out = new Map<string, AgentTally>();
	for (const c of calls) {
		const key = agentKey(c.client, c.token_name);
		const entry = out.get(key) ?? { key, client: c.client, token: c.token_name, count: 0 };
		entry.count += 1;
		out.set(key, entry);
	}
	return [...out.values()].sort((a, b) => b.count - a.count);
}

export interface LiveSession {
	client: string;
	last: string;
}

export function sessionsByToken(sessions: McpSession[]): Map<string, LiveSession[]> {
	const out = new Map<string, LiveSession[]>();
	for (const s of sessions) {
		const list = out.get(s.token_id) ?? [];
		list.push({ client: s.client, last: s.last_seen });
		out.set(s.token_id, list);
	}
	return out;
}
