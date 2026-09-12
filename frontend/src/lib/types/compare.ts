export const CHANGE_VERB = {
	APPEARED: 'appeared',
	CHANGED: 'changed',
	DISAPPEARED: 'disappeared',
	UNCONFIRMED: 'unconfirmed',
	UNCHANGED: 'unchanged'
} as const;

export type ChangeVerb = (typeof CHANGE_VERB)[keyof typeof CHANGE_VERB];

export const VERB_ORDER: ChangeVerb[] = [
	CHANGE_VERB.APPEARED,
	CHANGE_VERB.CHANGED,
	CHANGE_VERB.DISAPPEARED,
	CHANGE_VERB.UNCONFIRMED,
	CHANGE_VERB.UNCHANGED
];

export const LISTED_VERBS: ChangeVerb[] = VERB_ORDER.slice(0, 4);

export const COMPARABILITY = {
	LIKE_FOR_LIKE: 'like_for_like',
	SETTINGS_DIFFER: 'settings_differ',
	QUALITY_DIFFERS: 'quality_differs',
	NOT_COVERED: 'not_covered'
} as const;

export type Comparability = (typeof COMPARABILITY)[keyof typeof COMPARABILITY];

export interface RunSide {
	scan_id: string;
	engine_name: string;
	context_name: string | null;
	intensity: string;
	scope: string;
	status: string;
	started_at: string | null;
	completed_at: string | null;
	duration_seconds: number | null;
	stages_ran: number;
	stages_planned: number;
	counts: Record<string, number>;
}

export interface StageDiff {
	name: string;
	title: string;
	baseline: string | null;
	current: string | null;
}

export interface SettingDiff {
	stage: string;
	title: string;
	field: string;
	label: string;
	before: string | null;
	after: string | null;
}

export interface RunDifference {
	key: string;
	label: string;
	baseline: string | null;
	current: string | null;
	material: boolean;
}

export interface CoverageLine {
	label: string;
	baseline: string | null;
	current: string | null;
}

export interface DimensionVerdict {
	dimension: string;
	comparability: Comparability;
	covered_baseline: boolean;
	covered_current: boolean;
	compared: boolean;
	confirmed: boolean;
	note: string;
	stages: string[];
	settings: SettingDiff[];
	coverage: CoverageLine[];
}

export interface DimensionDelta {
	dimension: string;
	label: string;
	noun: string;
	noun_plural: string;
	verdict: DimensionVerdict;
	total_baseline: number;
	total_current: number;
	appeared: number;
	changed: number;
	disappeared: number;
	unconfirmed: number;
	unchanged: number;
	intel_moved: number;
}

export interface ChangeFieldDelta {
	field: string;
	label: string;
	before: string | null;
	after: string | null;
	tone: 'up' | 'down' | 'neutral';
}

export interface ScreenshotPair {
	baseline: string | null;
	current: string | null;
}

export interface ChangeRow {
	key: string;
	dimension: string;
	verb: ChangeVerb;
	signal: string;
	rank: number;
	title: string;
	subtitle: string;
	scan_id: string;
	fields: ChangeFieldDelta[];
	severity: string | null;
	status: number | null;
	port: number | null;
	is_kev: boolean;
	sensitive: boolean;
	screenshots: ScreenshotPair | null;
}

export interface ChangeRows {
	dimension: string;
	items: ChangeRow[];
	total: number;
	page: number;
	size: number;
}

export interface ComparableRun {
	scan_id: string;
	engine_name: string;
	status: string;
	scope: string;
	started_at: string | null;
	duration_seconds: number | null;
	counts: Record<string, number>;
	dimensions: string[];
	comparable: boolean;
	reason: string;
}

export interface ScanComparison {
	target_id: string;
	target_value: string;
	target_type: string;
	baseline: RunSide;
	current: RunSide;
	dimensions: DimensionDelta[];
	stage_diff: StageDiff[];
	setting_diff: SettingDiff[];
	settings_identical: number;
	run_diff: RunDifference[];
	runs_between: number;
	comparability: Comparability;
	headline: string;
	summary: string;
	changes_total: number;
	live: boolean;
	suggestion: ComparableRun | null;
	generated_at: string;
}

export function listedCount(delta: DimensionDelta): number {
	return delta.appeared + delta.changed + delta.disappeared + delta.unconfirmed;
}

export function verbCount(delta: DimensionDelta, verb: ChangeVerb): number {
	return delta[verb] ?? 0;
}
