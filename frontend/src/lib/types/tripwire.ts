import type {
	ActionKind,
	CheckStatus,
	FireOn,
	ScopeKind,
	TripwireTrigger
} from '$lib/config/tripwires';
import type { QueryError } from '$lib/types/asset-query';

export interface NotifyAction {
	kind: ActionKind.Notify | 'notify';
	channel_ids: string[];
}

export interface ScanAction {
	kind: ActionKind.Scan | 'scan';
	stages: string[];
	intensity?: string | null;
}

export type TripwireAction = NotifyAction | ScanAction;

export interface TripwireScope {
	kind: ScopeKind | string;
	ids: string[];
}

export interface TripwireScopeRead extends TripwireScope {
	labels: string[];
}

export interface Tripwire {
	id: string;
	project_id: string;
	name: string;
	dimension: string;
	query: string;
	trigger: TripwireTrigger | string;
	fire_on: FireOn | string;
	scope: TripwireScopeRead;
	actions: TripwireAction[];
	enabled: boolean;
	fired_count: number;
	recent_fired: number;
	last_fired_at: string | null;
	last_checked_at: string | null;
	created_at: string;
	updated_at: string;
}

export interface TripwireCreate {
	name: string;
	dimension: string;
	query: string;
	trigger: string;
	fire_on: string;
	scope: TripwireScope;
	actions: TripwireAction[];
	enabled?: boolean;
}

export type TripwireUpdate = Partial<TripwireCreate>;

export interface FiredRow {
	key: string;
	label: string;
	detail: string;
	severity?: string | null;
	seed?: string | null;
}

export interface Outcome {
	kind: string;
	status: string;
	detail: string;
	scan_id: string | null;
}

export interface TripwireRun {
	id: string;
	tripwire_id: string;
	target_id: string;
	target_value: string;
	scan_id: string;
	status: CheckStatus | string;
	matched: number;
	fired: number;
	rows: FiredRow[];
	outcomes: Outcome[];
	detail: string | null;
	checked_at: string;
	fired_at: string | null;
}

export interface TripwireRunCounts {
	fired: number;
	quiet: number;
	total: number;
}

export interface TripwirePreviewRequest {
	dimension: string;
	query: string;
	fire_on: string;
	scope: TripwireScope;
}

export interface PreviewTarget {
	target_id: string;
	target_value: string;
	scan_id: string;
	status: CheckStatus | string;
	matched: number;
	fired: number;
	capped: boolean;
	completed_at: string | null;
}

export interface TripwirePreview {
	targets: PreviewTarget[];
	matched: number;
	fired: number;
	rows: FiredRow[];
	scanned: number;
	unscanned: number;
	capped: boolean;
	error: QueryError | null;
}

export interface TripwireBacktest {
	days: number;
	runs: PreviewTarget[];
	capped: boolean;
	error: QueryError | null;
}

export interface ChoiceSpec {
	key: string;
	label: string;
	help: string;
}

export interface TripwireTemplate {
	key: string;
	name: string;
	dimension: string;
	query: string;
	fire_on: string;
	trigger: string;
	group: string;
}

export interface TripwireDimension {
	key: string;
	label: string;
	noun: string;
	noun_plural: string;
	stages: string[];
	default_stages: string[];
}

export interface StageChoice {
	name: string;
	title: string;
}

export interface ChannelChoice {
	id: string;
	name: string;
	provider: string;
}

export interface TripwireCatalog {
	dimensions: TripwireDimension[];
	triggers: ChoiceSpec[];
	fire_modes: ChoiceSpec[];
	actions: ChoiceSpec[];
	stages: StageChoice[];
	templates: TripwireTemplate[];
	template_groups: ChoiceSpec[];
	channels: ChannelChoice[];
	max_tripwires: number;
	max_runs_per_day: number;
	recent_days: number;
}
