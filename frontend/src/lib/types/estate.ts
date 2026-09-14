export interface EstateSignal {
	kind: string;
	label: string;
	strength: string;
	detail: string;
	hosts: string[];
	count: number;
}

export interface EstateSource {
	target_id: string;
	target_value: string;
	scan_id: string | null;
}

export interface EstateDomain {
	domain: string;
	target_id: string | null;
	strength: number;
	signals: EstateSignal[];
	sources: EstateSource[];
}

export interface EstateProvider {
	name: string;
	kind: string;
	count: number;
	detail: string;
	query: string | null;
}

export interface EstateNeighbourCert {
	host: string;
	subject: string;
	names: number;
	provider: string | null;
}

export interface EstateCounts {
	untracked: number;
	tracked: number;
	providers: number;
	neighbour_names: number;
	by_reason: Record<string, number>;
}

export interface TargetEstate {
	target_id: string;
	scan_id: string | null;
	root: string;
	counts: EstateCounts;
	domains: EstateDomain[];
	providers: EstateProvider[];
	neighbours: EstateNeighbourCert[];
	own: string[];
	considered_targets: number;
}

export interface ProjectEstate {
	targets_examined: number;
	untracked: number;
	domains: EstateDomain[];
}
