export interface SurfaceTargetRead {
	target_id: string;
	target_value: string;
	target_type: string;
	scan_id: string | null;
	scan_status: string | null;
	observed_at: string | null;
	stale: boolean;
}

export interface SurfaceCoverage {
	dimension: string;
	label: string;
	noun: string;
	noun_plural: string;
	total: number;
	total_capped: boolean;
	targets_total: number;
	targets_covered: number;
	observed_from: string | null;
	observed_to: string | null;
	covered: SurfaceTargetRead[];
	uncovered: SurfaceTargetRead[];
}

export interface SurfaceOverview {
	project_id: string;
	targets_total: number;
	live_scans: number;
	exposures: number;
	cves: number;
	dimensions: SurfaceCoverage[];
	generated_at: string;
}
