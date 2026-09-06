export type RecheckTone = 'up' | 'down' | 'neutral';

export interface RecheckChange {
	field: string;
	label: string;
	before: string | null;
	after: string | null;
	tone: RecheckTone;
}

export interface Recheck {
	id: string;
	scan_id: string;
	parent_scan_id: string;
	dimension: string;
	asset_kind: string;
	asset_key: string;
	changed: boolean;
	changes: RecheckChange[];
	created_at: string;
	status: string;
	stage_titles: string[];
	duration_seconds: number | null;
}

export interface RescanDimension {
	dimension: string;
	label: string;
	noun: string;
	noun_plural: string;
	seed_kind: string;
	default_stages: string[];
}

export interface RescanSchema {
	dimensions: RescanDimension[];
	rescannable_stages: string[];
	max_assets: number;
}

export interface RescanCreate {
	parent_scan_id: string;
	dimension: string;
	assets: string[];
	stages?: string[];
	overrides?: Record<string, Record<string, unknown>>;
	context_id?: string | null;
	intensity?: string | null;
	template_ids?: string[];
}
