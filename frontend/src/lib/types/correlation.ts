export interface CorrelationHost {
	id: string;
	name: string;
	live: boolean;
	status: number | null;
	title: string | null;
	hubs: number;
}

export interface CorrelationHub {
	id: string;
	kind: string;
	value: string;
	label: string;
	count: number;
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
	hosts: number;
	common: number;
	platform: number;
}

export interface CorrelationGraph {
	hosts: CorrelationHost[];
	hubs: CorrelationHub[];
	kinds: CorrelationKindStat[];
	total_hosts: number;
	estate_hosts: number;
	shared_hosts: number;
	truncated: boolean;
}
