// mirrors shared/definitions/discovery_sources.py
export enum SourceStatus {
	FOUND = 'found',
	EMPTY = 'empty',
	FAILED = 'failed',
	SKIPPED = 'skipped'
}

export const SOURCES_KEY = 'sources';
export const UNKEYED_KEY = 'sources_without_key';
export const NOTE_KEY = 'sources_note';

export interface DiscoverySource {
	key: string;
	label: string;
	via: string | null;
	names: number;
	only: number;
	status: SourceStatus;
	note: string | null;
	keyed: boolean;
}

export function discoverySources(result: Record<string, unknown> | undefined): DiscoverySource[] {
	const rows = result?.[SOURCES_KEY];
	return Array.isArray(rows) ? (rows as DiscoverySource[]) : [];
}

export function unkeyedSources(result: Record<string, unknown> | undefined): number {
	const value = result?.[UNKEYED_KEY];
	return typeof value === 'number' ? value : 0;
}
