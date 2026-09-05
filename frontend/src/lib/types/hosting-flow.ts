export interface FlowNode {
	id: string;
	label: string;
	count: number;
	column: number;
	tone: string;
	query: string | null;
	detail: string | null;
}

export interface FlowLink {
	source: string;
	target: string;
	count: number;
	query: string | null;
}

export interface HostingFlow {
	hosts: number;
	resolving: number;
	networks: number;
	nodes: FlowNode[];
	links: FlowLink[];
}
