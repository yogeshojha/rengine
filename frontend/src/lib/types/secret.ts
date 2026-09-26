import type { QueryError } from './asset-query';
import type { SecretGroup, SecretSource, SecretState } from '$lib/config/secrets';

export interface SecretRead {
	id: string;
	scan_id: string;
	target_id: string;
	target_value: string | null;
	fingerprint: string;
	kind: string;
	kind_label: string;
	group: SecretGroup;
	group_label: string;
	vendor: string;
	state: SecretState;
	state_label: string;
	is_secret: boolean;
	value: string;
	subject: string | null;
	meta: Record<string, unknown>;
	host: string;
	url: string;
	http_asset_id: string | null;
	source: SecretSource;
	source_label: string;
	sightings: number;
	hosts: number;
	discovered_at: string;
	is_new: boolean;
}

export interface SecretSightingRead {
	id: string;
	host: string;
	url: string;
	http_asset_id: string | null;
	source: SecretSource;
	source_label: string;
	offset: number;
	context: string | null;
}

export interface SecretDetail extends SecretRead {
	context: string | null;
	sightings_shown: SecretSightingRead[];
	sightings_truncated: boolean;
}

export interface SecretPage {
	items: SecretRead[];
	total: number;
	total_capped: boolean;
	error?: QueryError | null;
}

export interface SecretFacet {
	key: string;
	label: string;
	count: number;
}

export interface SecretFacets {
	state: SecretFacet[];
	group: SecretFacet[];
	kind: SecretFacet[];
	vendor: SecretFacet[];
	source: SecretFacet[];
	subject: SecretFacet[];
}

export interface SecretCoverageRow {
	source: string;
	source_label: string;
	status: string;
	documents_total: number;
	documents_read: number;
	bytes_read: number;
	truncated: number;
	skipped: number;
	detectors: number;
	matches: number;
	secrets: number;
	dropped: Record<string, number>;
	error: string | null;
}

export interface SecretCoverage {
	ran: boolean;
	partial: boolean;
	scans: number;
	documents_total: number;
	documents_read: number;
	bytes_read: number;
	truncated: number;
	detectors: number;
	secrets: number;
	exposed: number;
	rows: SecretCoverageRow[];
}

export interface SecretFilter {
	q?: string;
	limit?: number;
	offset?: number;
	sort?: string;
	direction?: string;
}
