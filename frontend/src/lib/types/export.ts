export interface ExportRead {
	id: string;
	project_id: string;
	dimension: string;
	scope: 'scan' | 'target' | 'project';
	scan_id: string | null;
	target_id: string | null;
	subject: string;
	query: string;
	export_format: string;
	include_evidence: boolean;
	status: string;
	progress: number;
	step: string;
	error: string | null;
	filename: string | null;
	bytes_written: number;
	row_count: number;
	total_rows: number;
	capped: boolean;
	created_at: string;
	completed_at: string | null;
	duration_seconds: number | null;
	expires_at: string | null;
}

export interface ExportCreate {
	dimension: string;
	scan_id?: string | null;
	target_id?: string | null;
	export_format: string;
	filters?: Record<string, unknown>;
	include_evidence?: boolean;
}
