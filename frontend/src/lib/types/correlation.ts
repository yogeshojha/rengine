export interface CorrelationHost {
	id: string;
	name: string;
	live: boolean;
	status: number | null;
	title: string | null;
	hubs: number;
	target: string;
}

export interface CorrelationHub {
	id: string;
	kind: string;
	value: string;
	label: string;
	count: number;
	targets: number;
	share: number;
	common: boolean;
	platform: boolean;
	platform_label: string;
	query: string;
	members: number[];
}

export interface CorrelationKindStat {
	key: string;
	label: string;
	help: string;
	default: boolean;
	hubs: number;
	total: number;
	hosts: number;
	common: number;
	platform: number;
	crossing: number;
}

export interface CorrelationGraph {
	hosts: CorrelationHost[];
	hubs: CorrelationHub[];
	kinds: CorrelationKindStat[];
	total_hosts: number;
	estate_hosts: number;
	shared_hosts: number;
	targets_total: number;
	truncated: boolean;
}
