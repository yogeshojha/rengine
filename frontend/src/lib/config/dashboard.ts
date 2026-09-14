// mirrors shared/definitions/dashboard.py
export enum QueueTier {
	Act = 'act',
	Attend = 'attend',
	Track = 'track'
}
export const TIER_ORDER: QueueTier[] = [QueueTier.Act, QueueTier.Attend, QueueTier.Track];
export const TIER_LABELS: Record<QueueTier, string> = {
	[QueueTier.Act]: 'Act',
	[QueueTier.Attend]: 'Attend',
	[QueueTier.Track]: 'Track'
};
export const TIER_HELP: Record<QueueTier, string> = {
	[QueueTier.Act]: 'Known exploited, proven, likely exploited or critical',
	[QueueTier.Attend]: 'High or medium, corroborated, or a possible exploit',
	[QueueTier.Track]: 'Everything else'
};

export enum FunnelStep {
	Names = 'names',
	Resolved = 'resolved',
	Live = 'live',
	Origins = 'origins',
	Findings = 'findings'
}
export const FUNNEL_LABELS: Record<FunnelStep, string> = {
	[FunnelStep.Names]: 'Names found',
	[FunnelStep.Resolved]: 'Resolve',
	[FunnelStep.Live]: 'Answer HTTP',
	[FunnelStep.Origins]: 'Distinct origins',
	[FunnelStep.Findings]: 'With a finding'
};
export const FUNNEL_QUERY: Record<FunnelStep, string | null> = {
	[FunnelStep.Names]: '',
	[FunnelStep.Resolved]: 'is:resolved',
	[FunnelStep.Live]: 'is:live',
	[FunnelStep.Origins]: null,
	[FunnelStep.Findings]: 'is:vulnerable'
};
export const FUNNEL_DROP: Record<FunnelStep, string | null> = {
	[FunnelStep.Names]: 'unresolved',
	[FunnelStep.Resolved]: 'no HTTP answer',
	[FunnelStep.Live]: 'share an origin',
	[FunnelStep.Origins]: 'no finding',
	[FunnelStep.Findings]: null
};

export enum ActivityKind {
	Run = 'run',
	Watch = 'watch',
	Program = 'program',
	Feeds = 'feeds',
	Intel = 'intel',
	Connector = 'connector'
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
