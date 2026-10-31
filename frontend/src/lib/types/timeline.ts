import type {
	Observation,
	RenderFlag,
	RenderState,
	TimelineFlag,
	WebAssetState
} from '$lib/config/timeline';
import type { QueryError } from './asset-query';
import type { ScanStatus } from './scan';
import type { SubdomainRead } from './subdomain';
import type { SubdomainFilter } from '$lib/utilities/scan-insights';

export interface TimelineFilter extends SubdomainFilter {
	window: number;
	flag: TimelineFlag | null;
}

export interface TimelineScan {
	id: string;
	started_at: string | null;
	status: ScanStatus;
	observation: Observation;
}

export interface TimelineCell {
	state: WebAssetState;
	status: number | null;
	changed: string[];
}

export interface TimelineRow {
	host: SubdomainRead;
	cells: TimelineCell[];
	state: WebAssetState;
	flags: TimelineFlag[];
	transitions: number;
	attribute_changes: number;
	first_seen_at: string | null;
	last_change_scan_id: string | null;
}

export interface TimelineSearchResult {
	scans: TimelineScan[];
	items: TimelineRow[];
	total: number;
	counts: Record<string, number>;
	error: QueryError | null;
}

export interface RenderFilter extends SubdomainFilter {
	window: number;
	flag: RenderFlag | null;
}

export interface RenderCell {
	state: RenderState;
	path: string | null;
	distance: number | null;
}

export interface RenderRow {
	host: SubdomainRead;
	cells: RenderCell[];
	flags: RenderFlag[];
	changes: number;
	first_capture_at: string | null;
	last_change_scan_id: string | null;
}

export interface RenderSearchResult {
	scans: TimelineScan[];
	items: RenderRow[];
	total: number;
	counts: Record<string, number>;
	error: QueryError | null;
}
