import { API_PREFIX } from '$lib/api/client';
import type { CandidateState, ConnectorState, SourceTool } from '$lib/types/connector';

export const CONNECTOR_POLL_MS = 10_000;
export const CONNECT_POLL_MS = 2000;
export const LIVE_POLL_MS = 2500;
export const DELIVERY_POLL_MS = 1000;
export const DELIVERY_WAIT_MS = 12_000;
export const NEW_ROW_MS = 60_000;
export const SEND_SHORTCUT = 'b';

export const CONNECTOR_STATE_LABELS: Record<ConnectorState, string> = {
	idle: 'Not connected',
	live: 'Receiving',
	connected: 'Connected',
	stale: 'Offline',
	paused: 'Paused'
};

export const ONLINE_STATES = new Set<ConnectorState>(['live', 'connected']);

export const CONNECTOR_STATE_DOT: Record<ConnectorState, string> = {
	idle: 'bg-muted-foreground',
	live: 'bg-success',
	connected: 'bg-info',
	stale: 'bg-muted-foreground',
	paused: 'bg-muted-foreground'
};

export const SOURCE_TOOL_LABELS: Record<SourceTool, string> = {
	proxy: 'Proxy',
	repeater: 'Repeater',
	other: 'Other'
};

export const INGESTED_TOOLS: SourceTool[] = ['proxy', 'repeater'];

// mirrors shared/definitions/connectors.py:ActionKind
export enum ActionKind {
	REPEATER = 'repeater',
	INTRUDER = 'intruder',
	ORGANIZER = 'organizer',
	SITE_MAP = 'sitemap'
}

export const HANDOFF_KINDS: ActionKind[] = [
	ActionKind.REPEATER,
	ActionKind.INTRUDER,
	ActionKind.ORGANIZER,
	ActionKind.SITE_MAP
];

export const DEFAULT_ACTION_KIND = ActionKind.REPEATER;

export const ACTION_KIND_LABELS: Record<ActionKind, string> = {
	[ActionKind.REPEATER]: 'Repeater',
	[ActionKind.INTRUDER]: 'Intruder',
	[ActionKind.ORGANIZER]: 'Organizer',
	[ActionKind.SITE_MAP]: 'Site map'
};

export const MAX_HANDOFF = 200;

export const CANDIDATE_STATES: CandidateState[] = ['new', 'queued', 'scanned', 'ignored'];

export const CANDIDATE_STATE_LABELS: Record<CandidateState, string> = {
	new: 'New',
	queued: 'Queued',
	scanned: 'Scanned',
	ignored: 'Ignored'
};

export const NOTICE_LABELS: Record<string, string> = {
	sensitive: 'Sensitive path',
	admin: 'Administrative interface',
	unseen_by_scans: 'Not found by any scan',
	new_params: 'Parameters not seen by scans',
	server_error: 'Server error',
	non_standard_method: 'Uncommon method',
	out_of_scope: 'Out of scope'
};

export const NOTICE_HELP: Record<string, string> = {
	sensitive: 'The path matches a pattern associated with sensitive files.',
	admin: 'The path matches an administrative or authentication surface.',
	unseen_by_scans: 'A scan covered this target and did not record this path.',
	new_params: 'A scan recorded this path with a different parameter set.',
	server_error: 'The server returned a 5xx response.',
	non_standard_method: 'The method is not GET, POST, PUT, PATCH, DELETE, HEAD or OPTIONS.',
	out_of_scope: 'A bug bounty program lists this host as out of scope.'
};

const NOTICE_TONE: Record<string, string> = {
	out_of_scope: 'text-destructive font-medium',
	sensitive: 'text-destructive',
	server_error: 'text-destructive',
	admin: 'text-warning',
	unseen_by_scans: 'text-info',
	new_params: 'text-info'
};

export function noticeTone(notice: string): string {
	return NOTICE_TONE[notice] ?? 'text-muted-foreground';
}

const INGEST_PATH = `${API_PREFIX}/connectors/ingest`;

export function ingestEndpoint(): string {
	if (typeof location === 'undefined') return INGEST_PATH;
	return `${location.origin}${INGEST_PATH}`;
}

const CLIENT_VERSION = /(\d+\.\d+\.\d+)/;

export function clientVersion(value: string | null | undefined): string | null {
	return value ? (CLIENT_VERSION.exec(value)?.[1] ?? null) : null;
}

export function isOutdated(client: string | null, shipped: string | null | undefined): boolean {
	const running = clientVersion(client);
	const current = clientVersion(shipped);
	return running !== null && current !== null && running !== current;
}
