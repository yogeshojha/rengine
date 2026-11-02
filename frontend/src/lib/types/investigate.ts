import type { AskTraceStep } from './ask';

export interface InvestigatePlan {
	id: string;
	kind: string;
	kind_label: string;
	template_id: string;
	template_name: string | null;
	host: string;
	reason: string | null;
	state: string;
	state_label: string;
	refusal_reason: string | null;
	refusal_label: string | null;
	request_count: number | null;
	approved_by: string | null;
	approved_at: string | null;
	launched_scan_id: string | null;
	result: string | null;
	result_label: string | null;
	created_at: string;
}

export interface Investigation {
	id: string;
	target_id: string;
	scan_id: string;
	dimension: string;
	fingerprint: string;
	verdict: string;
	verdict_label: string;
	verified: boolean;
	rationale: string | null;
	trace: AskTraceStep[];
	by_rule: boolean;
	started_by: string | null;
	requests_spent: number;
	verified_at: string | null;
	model: string | null;
	cost_usd: number | null;
	plans: InvestigatePlan[];
	created_at: string;
	updated_at: string;
}

export interface InvestigateBrief {
	investigation: Investigation | null;
	available: boolean;
	off_reason: string | null;
	model: string | null;
}

export type InvestigateFrame =
	| { event: 'trace'; data: AskTraceStep & { index: number } }
	| { event: 'delta'; data: { text: string } }
	| { event: 'done'; data: Investigation }
	| { event: 'error'; data: { message: string } };
