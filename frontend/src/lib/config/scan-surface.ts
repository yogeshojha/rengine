// mirrors shared/definitions/scan_surface.py

export enum SurfaceClass {
	ROOT = 'root',
	NAME = 'name',
	SERVICE = 'service',
	BASE = 'base',
	REQUEST = 'request'
}

export const SURFACE_CLASS_LABELS: Record<string, string> = {
	[SurfaceClass.ROOT]: 'Site root',
	[SurfaceClass.NAME]: 'Hostname',
	[SurfaceClass.SERVICE]: 'Network service',
	[SurfaceClass.BASE]: 'Directory',
	[SurfaceClass.REQUEST]: 'Request'
};

export enum DropReason {
	OUT_OF_SCOPE = 'out_of_scope',
	DUPLICATE_SPELLING = 'duplicate_spelling',
	COVERED_BY_ORIGIN = 'covered_by_origin',
	NO_ANSWER = 'no_answer',
	CANARY_MATCH = 'canary_match',
	BUDGET = 'budget',
	OVER_CAP = 'over_cap'
}

export const DROP_REASON_LABELS: Record<string, string> = {
	[DropReason.OUT_OF_SCOPE]: 'Excluded by the scan context',
	[DropReason.DUPLICATE_SPELLING]: 'Same target, another spelling',
	[DropReason.COVERED_BY_ORIGIN]: 'Covered by an equivalent web asset',
	[DropReason.NO_ANSWER]: 'Did not answer',
	[DropReason.CANARY_MATCH]: 'Answers like a missing page',
	[DropReason.BUDGET]: 'Not reached within the time budget',
	[DropReason.OVER_CAP]: 'Over the target budget'
};

export enum ClusterSignal {
	ADDRESS = 'address',
	CERTIFICATE = 'certificate',
	BODY = 'body',
	SHAPE = 'shape',
	STATUS = 'status',
	TITLE = 'title',
	CANARY = 'canary',
	FAVICON = 'favicon'
}

export const CLUSTER_SIGNAL_LABELS: Record<string, string> = {
	[ClusterSignal.ADDRESS]: 'Same address',
	[ClusterSignal.CERTIFICATE]: 'Same certificate',
	[ClusterSignal.BODY]: 'Same body',
	[ClusterSignal.SHAPE]: 'Same response shape',
	[ClusterSignal.STATUS]: 'Same status',
	[ClusterSignal.TITLE]: 'Same title',
	[ClusterSignal.CANARY]: 'Same missing-page answer',
	[ClusterSignal.FAVICON]: 'Same favicon'
};

export enum Tier {
	ONE_REQUEST = 'one_request',
	UNIVERSAL = 'universal',
	MATCHED = 'matched',
	BLIND = 'blind',
	SERVICES = 'services',
	NAMES = 'names',
	REPLAY = 'replay',
	DAST = 'dast',
	BASES = 'bases'
}

export const TIER_ORDER: string[] = [
	Tier.ONE_REQUEST,
	Tier.UNIVERSAL,
	Tier.SERVICES,
	Tier.NAMES,
	Tier.MATCHED,
	Tier.BLIND,
	Tier.REPLAY,
	Tier.DAST,
	Tier.BASES
];

export const TIER_LABELS: Record<string, string> = {
	[Tier.ONE_REQUEST]: 'One-request checks',
	[Tier.UNIVERSAL]: 'Universal checks',
	[Tier.MATCHED]: 'Checks for detected software',
	[Tier.BLIND]: 'Remaining checks',
	[Tier.SERVICES]: 'TLS and network checks',
	[Tier.NAMES]: 'DNS checks',
	[Tier.REPLAY]: 'Confirmation on equivalent web assets',
	[Tier.DAST]: 'Fuzzing',
	[Tier.BASES]: 'Directory exposure checks'
};

export const TIER_HELP: Record<string, string> = {
	[Tier.ONE_REQUEST]: 'Checks that read the root page. Every web asset, ten requests at most.',
	[Tier.UNIVERSAL]: 'Checks that apply to any web server. One web asset per origin.',
	[Tier.MATCHED]: 'Checks for the software the web asset was seen running.',
	[Tier.BLIND]: 'Software-specific checks for software not detected. Runs last.',
	[Tier.SERVICES]: 'Certificate and protocol checks on open ports.',
	[Tier.NAMES]: 'Record-level checks on resolved names.',
	[Tier.REPLAY]: 'A finding re-run against each web asset the origin stands for.',
	[Tier.DAST]: 'Parameter fuzzing on discovered requests.',
	[Tier.BASES]: 'Exposure checks under each discovered directory.'
};

export enum SurfaceState {
	PLANNED = 'planned',
	SCANNED = 'scanned',
	PARTIAL = 'partial',
	COVERED = 'covered',
	NOT_SCANNED = 'not_scanned'
}

export const SURFACE_STATE_LABELS: Record<string, string> = {
	[SurfaceState.PLANNED]: 'Planned',
	[SurfaceState.SCANNED]: 'Scanned',
	[SurfaceState.PARTIAL]: 'Partly scanned',
	[SurfaceState.COVERED]: 'Covered by an equivalent web asset',
	[SurfaceState.NOT_SCANNED]: 'Not scanned'
};

export function tierOutcome(stamp: string | undefined): string | null {
	if (!stamp) return null;
	return stamp.split('@', 1)[0] || null;
}
