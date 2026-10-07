export interface CloudBucket {
	id: string;
	scan_id: string;
	target_id: string;
	name: string;
	provider: string;
	url: string;
	source: string;
	access: string;
	region: string | null;
	object_count: number | null;
	size: number | null;
	first_seen: string;
	discovered_at: string;
	state: string;
}

export interface CloudBucketSummary {
	covered: boolean;
	scan_id: string | null;
	target_id: string | null;
	observed_at: string | null;
	candidates: number | null;
	rows: CloudBucket[];
	access_counts: Record<string, number>;
	provider_counts: Record<string, number>;
	open_count: number;
	total: number;
}
