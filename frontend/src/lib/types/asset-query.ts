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
}

export interface QuerySchema {
	max_length: number;
	max_terms: number;
	groups: string[];
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
	groups: [],
	fields: [],
	operators: [],
	connectors: [],
	flags: [],
	examples: []
};
