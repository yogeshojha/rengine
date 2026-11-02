/** Mirror of shared/definitions/investigate.py */

export const INVESTIGATE_FEATURE = 'investigate';

export const MAX_PLAN_REQUESTS = 10;
export const MAX_INVESTIGATION_REQUESTS = 40;
export const MAX_PLANS = 8;

export const Verdict = {
	PENDING: 'pending',
	REPRODUCED: 'reproduced',
	CONFIRMED: 'confirmed',
	NOT_REPRODUCED: 'not_reproduced',
	FALSE_POSITIVE: 'false_positive',
	NEEDS_PERSON: 'needs_person'
} as const;
export type VerdictValue = (typeof Verdict)[keyof typeof Verdict];

export const VERDICT_LABELS: Record<string, string> = {
	[Verdict.PENDING]: 'Open',
	[Verdict.REPRODUCED]: 'Reproduced',
	[Verdict.CONFIRMED]: 'Confirmed from evidence',
	[Verdict.NOT_REPRODUCED]: 'Not reproduced',
	[Verdict.FALSE_POSITIVE]: 'False positive',
	[Verdict.NEEDS_PERSON]: 'Needs a person'
};

export const VERDICT_HELP: Record<string, string> = {
	[Verdict.PENDING]: 'No verdict yet.',
	[Verdict.REPRODUCED]: 'The check ran again and matched.',
	[Verdict.CONFIRMED]: 'The stored evidence is conclusive on its own.',
	[Verdict.NOT_REPRODUCED]: 'The check ran again and did not match.',
	[Verdict.FALSE_POSITIVE]: 'The stored evidence contradicts the match.',
	[Verdict.NEEDS_PERSON]: 'Verification needs a step the agent does not take.'
};

export const VERIFIED_VERDICTS: string[] = [Verdict.REPRODUCED, Verdict.CONFIRMED];

export function verdictLabel(value: string | null | undefined): string {
	return VERDICT_LABELS[value ?? ''] ?? VERDICT_LABELS[Verdict.PENDING];
}

export function isVerified(value: string | null | undefined): boolean {
	return VERIFIED_VERDICTS.includes(value ?? '');
}

export const PlanKind = {
	REPLAY: 'replay',
	CHECK: 'check'
} as const;
export type PlanKindValue = (typeof PlanKind)[keyof typeof PlanKind];

export const PLAN_LABELS: Record<string, string> = {
	[PlanKind.REPLAY]: 'Replay the check',
	[PlanKind.CHECK]: 'Run a check'
};

export const PlanState = {
	PROPOSED: 'proposed',
	REFUSED: 'refused',
	APPROVED: 'approved',
	RUNNING: 'running',
	DONE: 'done',
	DECLINED: 'declined',
	FAILED: 'failed'
} as const;
export type PlanStateValue = (typeof PlanState)[keyof typeof PlanState];

export const PLAN_STATE_LABELS: Record<string, string> = {
	[PlanState.PROPOSED]: 'Proposed',
	[PlanState.REFUSED]: 'Refused',
	[PlanState.APPROVED]: 'Approved',
	[PlanState.RUNNING]: 'Running',
	[PlanState.DONE]: 'Done',
	[PlanState.DECLINED]: 'Declined',
	[PlanState.FAILED]: 'Failed'
};

export const PlanResult = {
	REPRODUCED: 'reproduced',
	NOT_REPRODUCED: 'not_reproduced',
	ERROR: 'error'
} as const;
export type PlanResultValue = (typeof PlanResult)[keyof typeof PlanResult];

export const PLAN_RESULT_LABELS: Record<string, string> = {
	[PlanResult.REPRODUCED]: 'Reproduced',
	[PlanResult.NOT_REPRODUCED]: 'Not reproduced',
	[PlanResult.ERROR]: 'Did not run'
};

export const RefusalReason = {
	INTRUSIVE: 'intrusive',
	DOS: 'dos',
	FUZZ: 'fuzz',
	CALLBACK: 'callback',
	CREDENTIALS: 'credentials',
	OUT_OF_SCOPE: 'out_of_scope',
	REQUESTS: 'requests',
	BUDGET: 'budget'
} as const;
export type RefusalReasonValue = (typeof RefusalReason)[keyof typeof RefusalReason];

export const REFUSAL_LABELS: Record<string, string> = {
	[RefusalReason.INTRUSIVE]: 'Tagged intrusive',
	[RefusalReason.DOS]: 'Tagged for denial of service',
	[RefusalReason.FUZZ]: 'Fuzzes the target',
	[RefusalReason.CALLBACK]: 'Needs a callback',
	[RefusalReason.CREDENTIALS]: 'Sends credentials',
	[RefusalReason.OUT_OF_SCOPE]: 'Host is not under this target',
	[RefusalReason.REQUESTS]: 'Sends too many requests',
	[RefusalReason.BUDGET]: 'Request budget is spent'
};

export const REFUSAL_HELP: Record<string, string> = {
	[RefusalReason.INTRUSIVE]: 'The check is tagged intrusive and runs only by hand.',
	[RefusalReason.DOS]: 'The check is tagged for denial of service.',
	[RefusalReason.FUZZ]: 'The check fuzzes parameters and runs only by hand.',
	[RefusalReason.CALLBACK]:
		'The check proves itself through a callback listener that is not configured.',
	[RefusalReason.CREDENTIALS]: 'The check authenticates against the target.',
	[RefusalReason.OUT_OF_SCOPE]: 'The host does not sit under the finding’s target.',
	[RefusalReason.REQUESTS]: 'The check sends more requests than a replay allows.',
	[RefusalReason.BUDGET]: 'The investigation reached its request budget.'
};

export const StreamEvent = {
	TRACE: 'trace',
	DELTA: 'delta',
	DONE: 'done',
	ERROR: 'error'
} as const;
export type StreamEventValue = (typeof StreamEvent)[keyof typeof StreamEvent];
