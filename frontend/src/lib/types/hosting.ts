export interface HostingSlice {
	kind: string;
	label: string;
	count: number;
	query: string | null;
}

export interface HostingNetwork {
	id: string;
	label: string;
	detail: string | null;
	count: number;
	query: string | null;
	fronting: HostingSlice[];
}

export interface HostingComposition {
	hosts: number;
	resolving: number;
	attributed: number;
	networks: number;
	fronting: HostingSlice[];
	by_network: HostingNetwork[];
}
