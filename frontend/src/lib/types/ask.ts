import type {
	AskFlagValue,
	BlockKindValue,
	FollowUpSourceValue,
	ReadKindValue,
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
	blocks?: AnswerBlock[];
	follow_ups?: FollowUp[];
	about?: string | null;
	intelligent?: boolean;
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

// ---------- the estate ----------

export interface AnswerBlock {
	id: string;
	kind: BlockKindValue;
	dimension: string | null;
	query: string | null;
	group_by: string | null;
	cve: string | null;
	title: string | null;
	total: number | null;
	capped: boolean;
	about: string | null;
	edited: boolean;
	cause_key?: string | null;
}

export interface BlockGroup {
	value: string;
	label: string;
	count: number;
	query: string | null;
}

export type BlockRow = Record<string, unknown>;

export interface CveLadderRung {
	evidence: string;
	count: number;
	software: number;
	findings: number;
	help?: string;
}

export interface CveRecord {
	cve: string;
	known: boolean;
	severity: string | null;
	cvss_score: number | null;
	cvss_vector: string | null;
	description: string;
	published_at: string | null;
	epss_score: number | null;
	epss_percentile: number | null;
	is_kev: boolean;
	kev_ransomware: boolean;
	kev_date_added: string | null;
	kev_due_date: string | null;
	kev_required_action: string | null;
	exploit_score: number;
	assets: number;
	targets: number;
	first_seen: string | null;
	ladder: CveLadderRung[];
	by_target: { target: string; assets: number }[];
	locations: {
		host: string | null;
		ip: string | null;
		port: number | null;
		evidence: string;
		dimension: string;
		target: string | null;
	}[];
	locations_total: number;
	suppressed: number;
	corpus_ready: boolean;
	finding_scans: number;
	checks: number;
}

export interface BlockCauseDetail {
	label: string;
	count: number;
	hint: string | null;
}

export interface BlockCause {
	value: string;
	label: string;
	count: number;
	query: string | null;
	who: string | null;
	details: BlockCauseDetail[];
}

export interface BlockCauses {
	key: string;
	one: string;
	many: string;
	prep: string;
	mono: boolean;
	address: boolean;
	total_groups: number;
	groups: BlockCause[];
}

export interface BlockFact {
	title: string;
	question: string;
	query: string;
	count: number;
	capped: boolean;
}

export interface ReadToken {
	kind: ReadKindValue;
	text: string;
	field: string | null;
	op: string | null;
	negated: boolean;
	hint: string | null;
}

export interface BlockData {
	id: string;
	kind: BlockKindValue;
	dimension: string | null;
	total: number | null;
	capped: boolean;
	rows: BlockRow[];
	groups: BlockGroup[];
	covered: number | null;
	record: CveRecord | null;
	scope_values: string[];
	error: string | null;
	causes?: BlockCauses | null;
	facts?: BlockFact[];
	reading?: ReadToken[];
	scope_total?: number | null;
	scope_capped?: boolean;
}

export interface FollowUp {
	text: string;
	source: FollowUpSourceValue;
	reason: string | null;
	dimension?: string | null;
	query?: string | null;
	title?: string | null;
	count?: number | null;
	capped?: boolean;
	about?: string | null;
}

export interface PinnedQuery {
	dimension: string;
	query: string | null;
	title: string | null;
}

export interface EstateScope {
	target_ids: string[];
	organization_id: string | null;
	tag_id: string | null;
	scan_id?: string | null;
}

export interface EstateScopeRead extends EstateScope {
	scan_at: string | null;
	scan_target: string | null;
	label: string;
	targets: number;
	filtered: boolean;
	links: string[];
}

export interface EstateThread {
	id: string;
	project_id: string;
	title: string;
	scope: EstateScopeRead;
	message_count: number;
	cost_usd: number | null;
	created_at: string;
	last_at: string;
}

export interface EstateThreadDetail {
	thread: EstateThread;
	messages: AskMessage[];
}

export interface StarterCause {
	key: string;
	value: string;
	label: string;
	count: number;
	one: string;
}

export interface EstateStarter {
	key: string;
	question: string;
	statement: string;
	dimension: string;
	query: string;
	count: number;
	capped: boolean;
	cause: StarterCause | null;
}

export interface EstateVital {
	dimension: string;
	count: number;
	capped: boolean;
}

export interface EstateStarters {
	filtered: boolean;
	scope_values: string[];
	starters: EstateStarter[];
	targets: number;
	vitals: EstateVital[];
	example: string | null;
}

export interface EstateScanOption {
	id: string;
	target: string;
	engine: string;
	status: string;
	scope: string;
	at: string | null;
}

export interface EstateStatus {
	available: boolean;
	off_reason: string | null;
	off_code: string | null;
	provider: string | null;
	model: string | null;
}

export interface EstateQuestion {
	text: string;
	about: string | null;
	intelligent: boolean;
	pinned?: PinnedQuery | null;
}

export type EstateStreamFrame =
	| { event: 'trace'; data: AskTraceStep & { index: number } }
	| { event: 'delta'; data: { text: string } }
	| { event: 'block'; data: { block: AnswerBlock; data: BlockData } }
	| {
			event: 'done';
			data: { question: AskMessage; answer: AskMessage; thread: EstateThread };
	  }
	| { event: 'error'; data: { message: string } };
