import type {
	AddressFlag,
	AddressState,
	CheckFlag,
	CheckState,
	FindingGroup,
	FindingState,
	FindingTimelineMode,
	LaneState,
	Observation,
	PortFlag,
	RenderFlag,
	RenderState,
	ServiceTimelineMode,
	TimelineFlag,
	WebAssetState
} from '$lib/config/timeline';
import type { ServiceFilter } from '$lib/utilities/services';
import type { QueryError } from './asset-query';
import type { ScanStatus } from './scan';
import type { SubdomainRead } from './subdomain';
import type { SubdomainFilter } from '$lib/utilities/scan-insights';
import type { VulnFilter, VulnerabilityRead } from '$lib/utilities/vulns';

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
	runs: number;
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
	runs: number;
	items: RenderRow[];
	total: number;
	counts: Record<string, number>;
	error: QueryError | null;
}

export interface ServiceTimelineFilter extends ServiceFilter {
	window: number;
	mode: ServiceTimelineMode;
	flag: AddressFlag | PortFlag | null;
}

export interface PortChange {
	port: number;
	protocol: string;
	service_name: string | null;
	product: string | null;
	version: string | null;
	first_on_address: boolean;
	first_on_target: boolean;
	open_since: string | null;
}

export interface AddressCell {
	state: AddressState;
	opened: PortChange[];
	closed: PortChange[];
	software: PortChange[];
}

export interface LaneCell {
	state: LaneState;
	service_id: string | null;
	software_changed: boolean;
}

export interface ServiceLane {
	port: number;
	protocol: string;
	service_name: string | null;
	service_class: string | null;
	product: string | null;
	version: string | null;
	open_now: boolean;
	cells: LaneCell[];
	first_seen_at: string | null;
	opened_scan_id: string | null;
	closed_scan_id: string | null;
	events: number;
	software_changes: number;
}

export interface ServiceAddressRow {
	ip: string;
	hosts: string[];
	host_count: number;
	asn_org: string | null;
	country: string | null;
	is_cdn: boolean;
	cells: AddressCell[];
	lanes: ServiceLane[];
	flags: AddressFlag[];
	open_now: number;
	changes: number;
	first_seen_at: string | null;
	last_change_scan_id: string | null;
}

export interface PortCell {
	state: AddressState;
	count: number;
	delta: number;
	added: string[];
	removed: string[];
	more: number;
}

export interface ServicePortRow {
	port: number;
	protocol: string;
	service_name: string | null;
	product: string | null;
	cells: PortCell[];
	flags: PortFlag[];
	now: number;
	peak: number;
	first_seen_at: string | null;
	last_change_scan_id: string | null;
}

export interface ServiceTimelineResult {
	scans: TimelineScan[];
	runs: number;
	mode: ServiceTimelineMode;
	addresses: ServiceAddressRow[];
	ports: ServicePortRow[];
	total: number;
	counts: Record<string, number>;
	error: QueryError | null;
}

export interface FindingTimelineFilter extends VulnFilter {
	window: number;
	mode: FindingTimelineMode;
	flag: FindingGroup | CheckFlag | null;
}

export interface FindingCell {
	state: FindingState;
}

export interface LifeSegment {
	state: FindingState;
	start: number;
	end: number;
	days: number | null;
}

export interface FindingLifespan {
	finding: VulnerabilityRead;
	group: FindingGroup;
	state: FindingState;
	cells: FindingCell[];
	segments: LifeSegment[];
	first_seen_at: string | null;
	open_since: string | null;
	open_days: number | null;
	fixed_at: string | null;
	fixed_scan_id: string | null;
	regressions: number;
	returned_at: string | null;
	returned_scan_id: string | null;
	not_tested_runs: number;
	tested_runs: number;
	is_new: boolean;
	triage_state: string;
	last_change_scan_id: string | null;
}

export interface RunPoint {
	scan_id: string;
	open: Record<string, number>;
	fixed: number;
	regressed: number;
	tested_checks: number | null;
	tested_origins: number | null;
}

export interface FindingStats {
	open_now: number | null;
	open_delta: number | null;
	untested: number;
	regressed: number;
	fixed: number;
	fixed_median_days: number | null;
	oldest_open_days: number | null;
	oldest_open_name: string | null;
	oldest_open_severity: string | null;
	runs: RunPoint[];
}

export interface CheckCell {
	state: CheckState;
	hosts: number;
	delta: number;
	added: string[];
	removed: string[];
	more: number;
}

export interface CheckRow {
	template_id: string;
	template_name: string;
	severity: string;
	is_kev: boolean;
	cells: CheckCell[];
	flags: CheckFlag[];
	hosts_now: number | null;
	peak: number;
	library_scan_id: string | null;
	first_seen_at: string | null;
	last_change_scan_id: string | null;
}

export interface CheckStats {
	checks: number;
	tested_checks: number | null;
	spread: number;
	shrank: number;
	cleared: number;
	library_new: number;
}

export interface FindingTimelineResult {
	scans: TimelineScan[];
	runs: number;
	mode: FindingTimelineMode;
	stats: FindingStats | null;
	check_stats: CheckStats | null;
	items: FindingLifespan[];
	checks: CheckRow[];
	total: number;
	counts: Record<string, number>;
	error: QueryError | null;
}
