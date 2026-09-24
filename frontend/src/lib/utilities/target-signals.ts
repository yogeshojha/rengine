export type SortKey = 'updated' | 'created' | 'name' | 'type' | 'expiry' | 'enrichment';
export type SortDir = 'asc' | 'desc';
export type SignalFilter =
	| 'expiring'
	| 'attention'
	| 'awaiting'
	| 'enriched'
	| 'monitored'
	| 'unscanned'
	| 'stale'
	| 'critical'
	| 'high'
	| 'medium';

export interface TargetSummary {
	total: number;
	expiring: number;
	attention: number;
	awaiting: number;
	enriched: number;
	monitored: number;
	unscanned: number;
	stale: number;
	critical: number;
	high: number;
	medium: number;
}

export const EMPTY_TARGET_SUMMARY: TargetSummary = {
	total: 0,
	expiring: 0,
	attention: 0,
	awaiting: 0,
	enriched: 0,
	monitored: 0,
	unscanned: 0,
	stale: 0,
	critical: 0,
	high: 0,
	medium: 0
};
