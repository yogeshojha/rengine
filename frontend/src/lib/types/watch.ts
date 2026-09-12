export enum WatchStatus {
	Active = 'active',
	Paused = 'paused'
}

export enum WatchHostState {
	New = 'new',
	Unresolved = 'unresolved',
	Known = 'known',
	OutOfScope = 'out_of_scope',
	Probing = 'probing',
	Quiet = 'quiet',
	Alerted = 'alerted',
	Muted = 'muted'
}

export enum WatchEventKind {
	WatchStarted = 'watch_started',
	WatchPaused = 'watch_paused',
	WatchResumed = 'watch_resumed',
	WatchUpdated = 'watch_updated',
	BaselineQueued = 'baseline_queued',
	ScopeAdded = 'scope_added',
	ScopeRemoved = 'scope_removed',
	HostAlerted = 'host_alerted',
	HostOutOfScope = 'host_out_of_scope',
	StreamError = 'stream_error'
}

export enum WatchCadence {
	Off = 'off',
	Daily = 'daily',
	Weekly = 'weekly',
	Monthly = 'monthly'
}

export interface WatchBaseline {
	schedule_id: string | null;
	engine_name: string | null;
	status: string | null;
	next_run_at: string | null;
	last_run_at: string | null;
	running: number;
}

export interface Watch {
	id: string;
	project_id: string;
	program_id: string;
	platform: string;
	handle: string;
	program_name: string;
	profile_picture: string | null;
	submission_state: string;
	status: WatchStatus;
	organization_id: string | null;
	context_id: string | null;
	engine_id: string | null;
	cadence: WatchCadence;
	intensity: string | null;
	rate_limit: number | null;
	probe_on_resolve: boolean;
	probe_engine_id: string | null;
	follow_scope: boolean;
	alert_unresolved: boolean;
	alert_query: string;
	channel_ids: string[];
	notify_in_app: boolean;
	watch_items: string[];
	items_total: number;
	unenforceable: string[];
	targets: number;
	hosts_seen: number;
	hosts_alerted: number;
	last_certificate_at: string | null;
	last_alert_at: string | null;
	last_error: string | null;
	baseline: WatchBaseline;
	seen_at: string | null;
	new_hosts: number;
	new_alerts: number;
	scope_changes: number;
	created_at: string;
	updated_at: string;
}

export interface WatchSettings {
	engine_id: string | null;
	cadence: WatchCadence;
	intensity: string | null;
	rate_limit: number | null;
	probe_on_resolve: boolean;
	probe_engine_id: string | null;
	follow_scope: boolean;
	alert_unresolved: boolean;
	alert_query: string;
	channel_ids: string[];
	notify_in_app: boolean;
}

export interface WatchCreate extends WatchSettings {
	project_id: string;
	run_baseline_now: boolean;
}

export type WatchUpdate = Partial<WatchSettings> & { status?: WatchStatus };

export interface WatchTargetPreview {
	value: string;
	type: string;
	exists: boolean;
	watched: boolean;
}

export interface WatchPreview {
	targets: WatchTargetPreview[];
	wildcards: number;
	domains: number;
	items: string[];
	items_total: number;
	excluded_hosts: number;
	excluded_ips: number;
	unenforceable: string[];
	existing: boolean;
}

export interface WatchHost {
	id: string;
	watch_id: string;
	target_id: string;
	name: string;
	state: WatchHostState;
	state_label: string;
	reason: string | null;
	matched_item: string | null;
	issuer: string | null;
	not_before: string | null;
	sightings: number;
	first_seen_at: string;
	last_seen_at: string;
	resolved_ips: string[];
	cname: string | null;
	is_wildcard: boolean;
	scan_id: string | null;
	probed_at: string | null;
	status_code: number | null;
	title: string | null;
	tech: string[];
	screenshot_path: string | null;
	alerted_at: string | null;
	alerts: number;
}

export interface WatchEvent {
	id: string;
	watch_id: string;
	kind: WatchEventKind;
	label: string;
	name: string | null;
	detail: string | null;
	created_at: string;
}

export interface WatchHostCounts {
	all: number;
	arrived: number;
	alerted: number;
	unresolved: number;
	known: number;
	out_of_scope: number;
}

export interface StreamStatus {
	running: boolean;
	reachable: boolean;
	items: number;
	started_at: string | null;
	updated_at: string | null;
	last_certificate_at: string | null;
	certificates_seen: number;
	last_error: string | null;
	last_error_at: string | null;
	version: string | null;
}

export type WatchHostFilter = 'all' | 'arrived' | 'alerted' | 'unresolved' | 'out_of_scope';
