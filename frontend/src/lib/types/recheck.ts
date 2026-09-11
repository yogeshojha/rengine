import type { ScanRead } from '$lib/types/scan';

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
	max_scans: number;
}

export interface SeedPick {
	value: string;
	scan_id?: string;
}

export interface QuerySelection {
	filter: Record<string, unknown>;
	scan_ids: string[];
}

export interface SeedSelection {
	dimension: string;
	picks?: SeedPick[];
	query?: QuerySelection | null;
	exclude?: string[];
}

export interface RescanCreate {
	parent_scan_id?: string | null;
	dimension?: string;
	assets?: string[];
	selection?: SeedSelection | null;
	stages?: string[];
	overrides?: Record<string, Record<string, unknown>>;
	context_id?: string | null;
	intensity?: string | null;
	template_ids?: string[];
}

export interface SeedGroupSummary {
	target_id: string;
	target_value: string;
	scan_id: string;
	count: number;
}

export interface RunPreview {
	dimension: string;
	seed_kind: string;
	asset_count: number;
	matched: number | null;
	target_count: number;
	capped: boolean;
	targets: SeedGroupSummary[];
	stage_titles: string[];
}

export interface FocusedRun {
	run_group_id: string;
	scans: ScanRead[];
	asset_count: number;
	matched: number | null;
	target_count: number;
	capped: boolean;
	stage_titles: string[];
}
