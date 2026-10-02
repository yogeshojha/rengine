/** Mirror of shared/definitions/ask.py */

export const MAX_QUESTION_CHARS = 4000;
export const MAX_STARTERS = 3;

export const Verdict = {
	PROFILE: 'profile',
	PROVEN: 'proven',
	LIKELY: 'likely',
	UNCERTAIN: 'uncertain',
	INSUFFICIENT: 'insufficient',
	FALSE_POSITIVE: 'false_positive'
} as const;
export type VerdictValue = (typeof Verdict)[keyof typeof Verdict];

export const FactTone = {
	FOR: 'for',
	AGAINST: 'against',
	UNKNOWN: 'unknown'
} as const;
export type FactToneValue = (typeof FactTone)[keyof typeof FactTone];

export const CitationKind = {
	FACT: 'fact',
	TOOL: 'tool',
	LINE: 'line'
} as const;
export type CitationKindValue = (typeof CitationKind)[keyof typeof CitationKind];

export const MessageRole = {
	USER: 'user',
	ASSISTANT: 'assistant'
} as const;
export type MessageRoleValue = (typeof MessageRole)[keyof typeof MessageRole];

export const EvidenceField = {
	REQUEST: 'request',
	RESPONSE: 'response',
	TITLE: 'title',
	NOTE: 'note',
	MATCHED_AT: 'matched_at'
} as const;

export const EVIDENCE_FIELD_LABELS: Record<EvidenceFieldValue, string> = {
	request: 'request',
	response: 'response',
	title: 'page title',
	note: 'triage reason',
	matched_at: 'matched URL'
};
export type EvidenceFieldValue = (typeof EvidenceField)[keyof typeof EvidenceField];

export const StreamEvent = {
	TRACE: 'trace',
	DELTA: 'delta',
	DONE: 'done',
	ERROR: 'error'
} as const;

export const TraceStatus = {
	RUNNING: 'running',
	DONE: 'done',
	FAILED: 'failed'
} as const;
export type TraceStatusValue = (typeof TraceStatus)[keyof typeof TraceStatus];

export const AskFlag = {
	INSTRUCTION_TEXT: 'instruction_text'
} as const;
export type AskFlagValue = (typeof AskFlag)[keyof typeof AskFlag];

export const ASK_FLAG_LABELS: Record<AskFlagValue, string> = {
	instruction_text: 'Response contains instructions addressed to a model'
};

export const Decision = {
	CONFIRMED: 'confirmed',
	FALSE_POSITIVE: 'false_positive',
	NONE: 'none'
} as const;
export type DecisionValue = (typeof Decision)[keyof typeof Decision];

export const NextStep = {
	FILE_ISSUE: 'file_issue',
	RESCAN: 'rescan',
	NONE: 'none'
} as const;
export type NextStepValue = (typeof NextStep)[keyof typeof NextStep];
