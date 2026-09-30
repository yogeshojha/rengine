import type { Grouping } from '$lib/config/issue-trackers';

export interface IssueTracker {
	id: string;
	name: string;
	kind: string;
	url: string;
	config_masked: Record<string, string>;
	destination: string | null;
	issue_type: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
	last_test_at: string | null;
	last_test_ok: boolean | null;
	last_test_message: string | null;
	issues_filed: number;
	issues_failed: number;
}

export interface IssueTrackerWrite {
	name?: string;
	kind?: string;
	url?: string | null;
	config?: Record<string, string>;
	destination?: string | null;
	issue_type?: string | null;
	is_active?: boolean;
}

export interface IssueTrackerTest {
	kind: string;
	url: string | null;
	config: Record<string, string>;
	tracker_id?: string | null;
}

export interface TestResult {
	success: boolean;
	message: string;
}

export interface TrackerOption {
	key: string;
	name: string;
}

export interface TrackerRoute {
	id: string;
	project_id: string;
	target_id: string | null;
	target_value: string | null;
	tracker_id: string;
	destination: string;
	issue_type: string | null;
}

export interface RouteWrite {
	project_id: string;
	target_id: string | null;
	tracker_id: string;
	destination: string;
	issue_type: string | null;
}

export interface FileSelection {
	fingerprints: string[];
	template_ids: string[];
	tracker_id?: string | null;
	destination?: string | null;
	issue_type?: string | null;
	grouping: Grouping;
	title?: string | null;
}

export interface PreviewBlock {
	kind: 'heading' | 'paragraph' | 'facts' | 'code' | 'list' | 'link';
	text: string;
	items: [string, string][];
	lines: string[];
	href: string;
	lang: string;
}

export interface PlannedIssue {
	tracker_name: string;
	destination: string;
	title: string;
	severity: string;
	grouped: boolean;
	findings: number;
	target_value: string;
	attach_to: string | null;
}

export interface FilingPlan {
	tracker_id: string | null;
	tracker_name: string | null;
	tracker_kind: string | null;
	destination: string | null;
	issue_type: string | null;
	grouping: Grouping;
	issues: PlannedIssue[];
	new_issues: number;
	attached: number;
	already_filed: number;
	not_filed: number;
	findings: number;
	preview: PreviewBlock[] | null;
	refusal: string | null;
}

export interface TrackedIssue {
	id: string;
	tracker_id: string;
	tracker_name: string;
	tracker_kind: string;
	target_id: string;
	target_value: string | null;
	template_id: string;
	severity: string;
	grouped: boolean;
	destination: string;
	title: string;
	state: string;
	external_key: string | null;
	url: string | null;
	remote_status: string | null;
	remote_category: string | null;
	error: string | null;
	findings: number;
	present: number;
	created_at: string;
	filed_at: string | null;
	status_read_at: string | null;
}

export interface FilingResult {
	new_issues: number;
	attached: number;
	already_filed: number;
	not_filed: number;
	issues: TrackedIssue[];
}

export interface TicketRef {
	issue_id: string;
	tracker_name: string;
	tracker_kind: string;
	state: string;
	external_key: string | null;
	url: string | null;
	remote_status: string | null;
	remote_category: string | null;
	error: string | null;
}
