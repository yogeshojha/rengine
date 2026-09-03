export type QueryFieldType =
	| 'string'
	| 'enum'
	| 'number'
	| 'bytes'
	| 'duration'
	| 'date'
	| 'ip'
	| 'text'
	| 'flag';

export interface QueryFieldSpec {
	name: string;
	type: QueryFieldType;
	group: string;
	description: string;
	example: string;
	aliases: string[];
	values: string[];
	facet: string | null;
	operators: string[];
	free_text: boolean;
	unit: string | null;
	dynamic_sub: string | null;
}

export interface QueryOperatorSpec {
	symbol: string;
	description: string;
}

export interface QueryFlagSpec {
	value: string;
	description: string;
}

export interface QueryExampleSpec {
	query: string;
	description: string;
	group: string;
	generic: boolean;
}

export interface QueryLead extends QueryExampleSpec {
	count: number;
	capped: boolean;
}

export type QueryStarter = QueryExampleSpec | QueryLead;

export interface QueryLeads {
	leads: QueryLead[];
	total: number;
	total_capped: boolean;
	filtered: boolean;
	computed: boolean;
}

export interface QueryGroupSpec {
	key: string;
	label: string;
	description: string;
}

export interface QueryGroup {
	value: string;
	label: string;
	count: number;
	query: string;
}

export interface QueryGroups {
	dimension: string;
	groups: QueryGroup[];
	total_groups: number;
	truncated: boolean;
	rows: number;
	covered: number;
}

export interface RelatedEvidence {
	hostname: string;
	seen_on: string;
}

export interface RelatedDomain {
	domain: string;
	reason: string;
	reason_label: string;
	reason_detail: string;
	hostnames: string[];
	hostname_count: number;
	evidence: RelatedEvidence[];
	is_target: boolean;
}

export interface RelatedDomains {
	domains: RelatedDomain[];
	root: string;
}

export interface QuerySchema {
	max_length: number;
	max_terms: number;
	noun: string;
	noun_plural: string;
	groups: string[];
	example_groups: string[];
	group_dimensions: QueryGroupSpec[];
	fields: QueryFieldSpec[];
	operators: QueryOperatorSpec[];
	connectors: QueryOperatorSpec[];
	flags: QueryFlagSpec[];
	examples: QueryExampleSpec[];
}

export interface QueryError {
	message: string;
	hint: string | null;
	start: number;
	end: number;
}

export interface MatchEvidence {
	field: string;
	label: string;
	term: string;
	snippet: string | null;
}

export const EMPTY_QUERY_SCHEMA: QuerySchema = {
	max_length: 2000,
	max_terms: 8,
	noun: 'host',
	noun_plural: 'hosts',
	groups: [],
	example_groups: [],
	group_dimensions: [],
	fields: [],
	operators: [],
	connectors: [],
	flags: [],
	examples: []
};
