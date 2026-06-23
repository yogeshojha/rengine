export interface TakeoverCandidate {
	name: string;
	target_id: string;
	cname: string;
	provider: string;
	last_seen: string;
}

export interface TakeoverSignal {
	count: number;
	items: TakeoverCandidate[];
}

export interface SpoofableDomain {
	target_id: string;
	target_value: string;
	reason: string;
}

export interface SpoofableSignal {
	count: number;
	items: SpoofableDomain[];
}

export interface StaleTarget {
	target_id: string;
	target_value: string;
	target_type: string;
	last_scanned_at: string | null;
}

export interface StaleSignal {
	never_scanned: number;
	stale: number;
	items: StaleTarget[];
}

export interface DashboardSignals {
	takeover: TakeoverSignal;
	spoofable: SpoofableSignal;
	stale: StaleSignal;
}
