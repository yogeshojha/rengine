export interface PortRead {
	id: string;
	scan_id: string;
	target_id: string;
	ip: string;
	number: number;
	protocol: string;
	state: string;
	service_name: string | null;
	source: string;
	discovered_at: string;
}

export interface PortSummary {
	total: number;
	by_service: Record<string, number>;
}
