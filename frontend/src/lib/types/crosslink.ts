export interface CrossLinkPeer {
	host: string;
	target_id: string | null;
	target_value: string;
}

export interface CrossLink {
	kind: string;
	label: string;
	value: string;
	query: string;
	peers: CrossLinkPeer[];
	targets: string[];
	hosts: number;
}

export function linkedTargets(links: CrossLink[]): string[] {
	return [...new Set(links.flatMap((l) => l.targets))].filter(Boolean).sort();
}
