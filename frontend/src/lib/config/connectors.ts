import type { CandidateState, ConnectorState, SourceTool, SyncTrigger } from '$lib/types/connector';

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

export const SYNC_TRIGGERS: SyncTrigger[] = ['manual', 'quiet', 'walked_away', 'session_end'];

export const SYNC_TRIGGER_LABELS: Record<SyncTrigger, string> = {
	manual: 'Manual',
	quiet: 'After a quiet period',
	walked_away: 'On host change',
	session_end: 'On disconnect'
};

export const SYNC_TRIGGER_HELP: Record<SyncTrigger, string> = {
	manual: 'The queue is scanned only on request.',
	quiet: 'Scans a host’s queue once the quiet period elapses with no further traffic to that host.',
	walked_away: 'Scans a host’s queue once traffic moves to a different host.',
	session_end: 'Scans the queue when the connector disconnects.'
};

export const SOURCE_TOOL_LABELS: Record<SourceTool, string> = {
	proxy: 'Proxy',
	repeater: 'Manual request',
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
	server_error: 'Server error',
	non_standard_method: 'Uncommon method',
	out_of_scope: 'Out of scope'
};

export const NOTICE_HELP: Record<string, string> = {
	sensitive: 'The path matches a pattern associated with sensitive files.',
	admin: 'The path matches an administrative or authentication surface.',
	unseen_by_scans: 'No scan of this target has recorded this request shape.',
	server_error: 'The server returned a 5xx response.',
	non_standard_method: 'The method is not GET, POST, HEAD or OPTIONS.',
	out_of_scope:
		'A bug bounty program lists this host as out of scope. Testing it is not authorised.'
};

export const LOUD_NOTICES = new Set(['sensitive', 'admin', 'server_error', 'out_of_scope']);

export function noticeTone(notice: string): string {
	if (notice === 'out_of_scope') return 'text-destructive font-medium';
	if (notice === 'sensitive' || notice === 'server_error') return 'text-destructive';
	if (notice === 'admin') return 'text-warning';
	return 'text-muted-foreground';
}
