export type SortKey = 'updated' | 'created' | 'name' | 'type' | 'expiry' | 'enrichment';
export type SortDir = 'asc' | 'desc';
export type SignalFilter = 'expiring' | 'attention' | 'awaiting' | 'enriched';

export interface TargetSummary {
	total: number;
	expiring: number;
	attention: number;
	awaiting: number;
	enriched: number;
}
