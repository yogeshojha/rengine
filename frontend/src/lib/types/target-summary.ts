import type { ScanRead } from './scan';

export interface SurfaceMetric {
	key: string;
	label: string;
	covered: boolean;
	value: number | null;
	previous: number | null;
	delta: number | null;
	added: number | null;
	gone: number | null;
	scan_id: string | null;
	scan_status: string | null;
	observed_at: string | null;
	current: boolean;
}

export interface TargetSeverityCount {
	severity: string;
	label: string;
	count: number;
}

export interface TargetRisk {
	scan_id: string | null;
	observed_at: string | null;
	total: number;
	actionable: number;
	kev: number;
	suppressed: number;
	by_severity: TargetSeverityCount[];
}

export interface TargetMonitoring {
	cadence: string;
	next_run_at: string | null;
}

export interface TargetSummaryRead {
	target_id: string;
	scans_total: number;
	scans_running: number;
	scans_failed: number;
	first_scan_at: string | null;
	last_completed_at: string | null;
	latest_scan: ScanRead | null;
	surface: SurfaceMetric[];
	risk: TargetRisk;
	sensitive_services: number | null;
	inventory_total: number;
	monitoring: TargetMonitoring | null;
}
