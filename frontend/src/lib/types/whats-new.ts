export interface NewItem {
	id: string;
	kind: string;
	at: string;
	value: string;
	detail: string | null;
	tone: string;
	status: number | null;
	title: string | null;
	tech: string[];
	ips: string[];
	source: string | null;
	source_label: string | null;
	screenshot_path: string | null;
	severity: string | null;
	is_kev: boolean;
	sensitive: boolean;
	asset_type: string | null;
	query: string | null;
	target_id: string | null;
	target_value: string | null;
	target_type: string | null;
	scan_id: string | null;
	watch_id: string | null;
	host_id: string | null;
	scope_id: string | null;
	platform: string | null;
	handle: string | null;
	program_name: string | null;
	program_url: string | null;
	importable: boolean;
	target_exists: boolean | null;
	scanned: boolean | null;
	muted: boolean;
}

export interface NewSection {
	kind: string;
	total: number;
	items: NewItem[];
}

export interface NewSubject {
	kind: string;
	id: string | null;
	label: string;
	target_id: string | null;
	target_value: string | null;
	target_type: string | null;
	platform: string | null;
	handle: string | null;
	watched: boolean;
	watch_id: string | null;
}

export interface NewGroup {
	id: string;
	subject: NewSubject;
	at: string;
	counts: Record<string, number>;
	sections: NewSection[];
	scan_id: string | null;
	scan_started_at: string | null;
	scan_status: string | null;
	previous_scan_id: string | null;
	severities: Record<string, number>;
	completed_at: string | null;
	evidence: NewEvidence[];
	more: number;
}

export interface NewEvidence {
	kind: string;
	label: string;
	count: number;
	severity: string | null;
	kev: number;
	query: string;
}

export interface NewDay {
	date: string;
	counts: Record<string, number>;
}

export interface NewFeed {
	since: string;
	until: string | null;
	basis: string;
	marked_at: string | null;
	window: string | null;
	counts: Record<string, number>;
	facts: Record<string, Record<string, number>>;
	daily: NewDay[];
	groups: NewGroup[];
	truncated: boolean;
	first_runs: number;
	visual: number;
}

export interface VisualPair {
	id: string;
	host: string;
	at: string;
	distance: number;
	before_path: string;
	after_path: string;
	before_status: number | null;
	after_status: number | null;
	before_title: string | null;
	after_title: string | null;
	before_tech: string[];
	after_tech: string[];
	before_server: string | null;
	after_server: string | null;
	moved: string[];
	silent: boolean;
	target_id: string;
	target_value: string;
	target_type: string;
	scan_id: string;
	previous_scan_id: string;
	query: string;
}

export interface VisualFeed {
	since: string;
	until: string | null;
	basis: string;
	window: string | null;
	total: number;
	silent: number;
	pairs: VisualPair[];
	truncated: boolean;
}

export interface VisualParams {
	since?: string;
	window?: string;
	day?: string;
	day_to?: string;
	target_id?: string;
	q?: string;
}

export interface NewMark {
	marked_at: string;
}

export interface NewUnseen {
	count: number;
	since: string | null;
}

export interface NewFeedParams {
	since?: string;
	window?: string;
	day?: string;
	day_to?: string;
	target_id?: string;
	platform?: string;
	handle?: string;
	kinds?: string;
	ring?: string;
	q?: string;
}
