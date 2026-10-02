import type {
	AskFlagValue,
	DecisionValue,
	NextStepValue,
	CitationKindValue,
	EvidenceFieldValue,
	FactToneValue,
	MessageRoleValue,
	TraceStatusValue,
	VerdictValue
} from '$lib/config/ask';

export interface AskFact {
	n: number;
	tone: FactToneValue;
	label: string;
	detail: string | null;
	field: EvidenceFieldValue | null;
	lines: number[];
}

export interface AskCitation {
	n: number;
	kind: CitationKindValue;
	label: string;
	detail: string | null;
	field: EvidenceFieldValue | null;
	lines: number[];
	pivot: string | null;
}

export interface AskTraceStep {
	tool: string;
	label: string;
	status: TraceStatusValue;
	rows: number | null;
	pivot: string | null;
	ms: number;
	detail: string | null;
	args: string | null;
}

export interface AskFlagRead {
	kind: AskFlagValue;
	field: EvidenceFieldValue;
	line: number;
	sample: string;
}

export interface AskBrief {
	verdict: VerdictValue;
	label: string;
	facts: AskFact[];
	available: boolean;
	off_reason: string | null;
	model: string | null;
	starters: string[];
}

export interface AskThread {
	id: string;
	target_id: string;
	dimension: string;
	asset_key: string;
	title: string;
	message_count: number;
	cost_usd: number | null;
	created_at: string;
	last_at: string;
}

export interface AskSuggestion {
	decision: DecisionValue;
	next: NextStepValue;
}

export interface AskMessage {
	id: string;
	role: MessageRoleValue;
	text: string;
	citations: AskCitation[];
	trace: AskTraceStep[];
	flags: AskFlagRead[];
	suggestion: AskSuggestion | null;
	model: string | null;
	input_tokens: number;
	output_tokens: number;
	cost_usd: number | null;
	created_at: string;
}

export interface AskThreadDetail {
	thread: AskThread;
	messages: AskMessage[];
}

export interface AskThreadCreate {
	target_id: string;
	dimension: string;
	asset_key: string;
	title?: string | null;
}

export interface AskSubject {
	dimension: string;
	key: string;
	targetId: string;
	scanId: string;
	projectId: string;
	label: string;
	briefId?: string;
	request?: string | null;
	response?: string | null;
	state?: string | null;
	reason?: string | null;
}

export interface AskQuestion {
	text: string;
	scan_id: string;
}

export type AskStreamFrame =
	| { event: 'trace'; data: AskTraceStep & { index: number } }
	| { event: 'delta'; data: { text: string } }
	| { event: 'done'; data: { question: AskMessage; answer: AskMessage; thread: AskThread } }
	| { event: 'error'; data: { message: string } };
