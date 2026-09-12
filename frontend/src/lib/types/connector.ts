export type ConnectorKind = 'burp';
export type ConnectorState = 'idle' | 'live' | 'stale' | 'paused';
export type CandidateState = 'new' | 'queued' | 'scanned' | 'ignored';
export type SourceTool = 'proxy' | 'repeater' | 'other';

export interface ConnectorSpec {
	kind: ConnectorKind;
	title: string;
	vendor: string;
	description: string;
	docs_url: string;
	source_path: string;
	client_file: string;
	download_url: string | null;
	tools: SourceTool[];
	supports_scope_push: boolean;
	available: boolean;
}

export interface Connector {
	id: string;
	project_id: string;
	kind: ConnectorKind;
	name: string;
	token_prefix: string;
	only_known_hosts: boolean;
	ingest_tools: SourceTool[];
	capture_bodies: boolean;
	record_hosts: boolean;
	include_static: boolean;
	scan_safe_methods_only: boolean;
	context_id: string | null;
	paused: boolean;
	state: ConnectorState;
	requests_seen: number;
	dropped_out_of_scope: number;
	candidates: number;
	queued: number;
	unseen: number;
	unassigned: number;
	flagged: number;
	out_of_scope: number;
	discovered: number;
	scans_launched: number;
	pending_actions: number;
	last_seen_at: string | null;
	last_client: string | null;
	last_scan_at: string | null;
	created_at: string;
}

export interface SetupStep {
	title: string;
	detail: string;
	code: string | null;
	lang: string | null;
}

export interface ConnectorCreated {
	connector: Connector;
	secret: string;
	setup: {
		endpoint: string;
		download_url: string | null;
		client_file: string;
		steps: SetupStep[];
	};
}

export interface ConnectorCreate {
	name: string;
	kind: ConnectorKind;
	project_id: string;
	only_known_hosts?: boolean;
	ingest_tools?: SourceTool[];
	capture_bodies?: boolean;
	record_hosts?: boolean;
	include_static?: boolean;
	scan_safe_methods_only?: boolean;
	context_id?: string | null;
}

export type ConnectorUpdate = Partial<Omit<ConnectorCreate, 'project_id' | 'kind'>> & {
	paused?: boolean;
};

export interface Candidate {
	id: string;
	target_id: string | null;
	url: string;
	host: string;
	path: string;
	methods: string[];
	params: string[];
	param_count: number;
	endpoint_class: string | null;
	interests: string[];
	notices: string[];
	status_code: number | null;
	content_type: string | null;
	content_length: number | null;
	title: string | null;
	authenticated: boolean;
	source_tool: SourceTool;
	request_sample: string | null;
	known: boolean;
	state: CandidateState;
	hits: number;
	scan_id: string | null;
	first_seen_at: string;
	last_seen_at: string;
}

export interface CandidatePage {
	rows: Candidate[];
	total: number;
	counts: Record<string, number>;
	hosts: { host: string; count: number; unknown: number }[];
}

export interface DiscoveredDomain {
	domain: string;
	reason: string;
	reason_label: string;
	reason_detail: string;
	hostnames: string[];
	hostname_count: number;
	requests: number;
	out_of_scope: boolean;
	program: string | null;
	first_seen_at: string;
	last_seen_at: string;
}

export interface TargetAdded {
	target_id: string;
	target_value: string;
	attached: number;
	scan_id: string | null;
}

export interface CandidateQuery {
	state?: string;
	host?: string;
	notice?: string;
	known?: boolean;
	search?: string;
	page?: number;
}
