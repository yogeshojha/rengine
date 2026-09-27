export interface DatasetRead {
	kind: string;
	label: string;
	description: string;
	rows_noun: string;
	status: string;
	status_label: string;
	rows: number | null;
	error: string | null;
	last_synced_at: string | null;
	last_attempt_at: string | null;
	duration_ms: number | null;
	auto_sync: boolean;
}

export interface DatasetSyncResult {
	queued: boolean;
	detail: string | null;
}

export interface QueueRead {
	name: string;
	label: string;
	service: string;
	workers: number;
}

export interface QueueHealth {
	responded: boolean;
	queues: QueueRead[];
}
