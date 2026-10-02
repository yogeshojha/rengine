// mirrors shared/definitions/dashboard.py
export enum QueueTier {
	Act = 'act',
	Attend = 'attend',
	Track = 'track'
}
export const STALE_DAYS = 30;
export const EXPIRING_DAYS = 30;
export const TIER_ACT_EPSS = 0.088;
export const TIER_ATTEND_EPSS = 0.01;
export const ACT_QUERY = `is:kev or is:ransomware or evidence:proven or epss:>=${TIER_ACT_EPSS} or severity:critical`;
const ATTEND_BASE = `severity:[high,medium] or epss:>=${TIER_ATTEND_EPSS}`;
export const TIER_QUERY: Record<QueueTier, string> = {
	[QueueTier.Act]: ACT_QUERY,
	[QueueTier.Attend]: `not (${ACT_QUERY}) and (${ATTEND_BASE})`,
	[QueueTier.Track]: `not (${ACT_QUERY}) and not (${ATTEND_BASE})`
};
export const INTEL_CHANGE_ROWS = 200;
export const SIGNAL_ROWS = 500;
export const TIER_ORDER: QueueTier[] = [QueueTier.Act, QueueTier.Attend, QueueTier.Track];
export const TIER_LABELS: Record<QueueTier, string> = {
	[QueueTier.Act]: 'Act',
	[QueueTier.Attend]: 'Attend',
	[QueueTier.Track]: 'Track'
};
export const TIER_HELP: Record<QueueTier, string> = {
	[QueueTier.Act]: 'Known exploited, proven, likely exploited or critical',
	[QueueTier.Attend]: 'High or medium, or a possible exploit',
	[QueueTier.Track]: 'Everything else'
};

export enum ActivityKind {
	Run = 'run',
	Watch = 'watch',
	Program = 'program',
	Feeds = 'feeds',
	Intel = 'intel',
	Connector = 'connector'
}

export enum ActivityTone {
	Neutral = 'neutral',
	Hot = 'hot',
	New = 'new'
}

export const SCAN_OUTCOME_ORDER = ['completed', 'failed', 'cancelled'] as const;
export const SCAN_OUTCOME_FILL: Record<(typeof SCAN_OUTCOME_ORDER)[number], string> = {
	completed: 'var(--chart-2)',
	failed: 'var(--destructive)',
	cancelled: 'var(--sev-info)'
};
export const SCAN_OUTCOME_LABELS: Record<(typeof SCAN_OUTCOME_ORDER)[number], string> = {
	completed: 'Completed',
	failed: 'Failed',
	cancelled: 'Cancelled'
};

export const PROGRAM_EVENT_FILL: Record<string, string> = {
	program_added: 'var(--chart-1)',
	scope_added: 'var(--chart-2)',
	scope_removed: 'var(--chart-4)',
	program_went_public: 'var(--chart-3)'
};

export const CERT_BUCKET_FILL: Record<string, string> = {
	expired: 'var(--destructive)',
	week: 'var(--chart-4)',
	month: 'var(--chart-4)',
	quarter: 'var(--series)',
	later: 'var(--series)'
};

export const SURFACE_RISK_ROWS = 6;

export const DASHBOARD_SCOPE_PARAMS = {
	target: 'target',
	organization: 'org',
	tag: 'tag'
} as const;
