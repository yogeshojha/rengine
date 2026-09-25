export interface LookalikeRead {
	id: string;
	scan_id: string;
	target_id: string;
	apex: string;
	domain: string;
	display: string;
	technique: string;
	verdict: string;
	link_reason: string | null;
	a: string[];
	aaaa: string[];
	mx: string[];
	ns: string[];
	parked: boolean;
	http_status: number | null;
	final_url: string | null;
	title: string | null;
	similarity: number | null;
	registered_at: string | null;
	registrar: string | null;
	first_seen: string;
	discovered_at: string;
	state: string;
}

export interface LookalikeSummary {
	covered: boolean;
	scan_id: string | null;
	target_id: string | null;
	observed_at: string | null;
	apex: string | null;
	permutations: number | null;
	fetched: boolean;
	rows: LookalikeRead[];
	verdicts: Record<string, number>;
	open_threats: number;
	registered: number;
}
