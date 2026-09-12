import type { CandidateState, ConnectorState, SourceTool } from '$lib/types/connector';

export const CONNECTOR_POLL_MS = 10_000;

export const CONNECTOR_STATE_LABELS: Record<ConnectorState, string> = {
	idle: 'Not connected',
	live: 'Receiving',
	stale: 'Idle',
	paused: 'Paused'
};

export const CONNECTOR_STATE_DOT: Record<ConnectorState, string> = {
	idle: 'bg-muted-foreground',
	live: 'bg-success',
	stale: 'bg-warning',
	paused: 'bg-muted-foreground'
};

export const SOURCE_TOOL_LABELS: Record<SourceTool, string> = {
	proxy: 'Proxy',
	repeater: 'Repeater',
	other: 'Other'
};

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
	non_standard_method: 'The method is not GET, POST, HEAD or OPTIONS.',
	out_of_scope: 'A bug bounty program lists this host as out of scope.'
};

export const LOUD_NOTICES = new Set(['sensitive', 'admin', 'server_error', 'out_of_scope']);

export function noticeTone(notice: string): string {
	if (notice === 'out_of_scope') return 'text-destructive font-medium';
	if (notice === 'sensitive' || notice === 'server_error') return 'text-destructive';
	if (notice === 'admin') return 'text-warning';
	if (notice === 'unseen_by_scans' || notice === 'new_params') return 'text-info';
	return 'text-muted-foreground';
}

export const INGEST_PATH = '/api/v1/connectors/ingest';

export function ingestEndpoint(): string {
	if (typeof location === 'undefined') return INGEST_PATH;
	return `${location.origin}${INGEST_PATH}`;
}
