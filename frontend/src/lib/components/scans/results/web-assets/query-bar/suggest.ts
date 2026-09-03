import type { CaretContext } from '$lib/utilities/query-lexer';
import { quoteValue } from '$lib/utilities/query-lexer';
import type { Facet } from '$lib/utilities/scan-insights';
import type { QueryFieldSpec, QuerySchema } from '$lib/types/asset-query';

export interface Suggestion {
	id: string;
	insert: string;
	label: string;
	detail?: string;
	hint?: string;
	group: string;
	keepOpen?: boolean;
}

const MAX_PER_GROUP = 8;
const CONNECTOR_SUGGESTIONS = [
	{ value: 'and', detail: 'Both sides must match' },
	{ value: 'or', detail: 'Either side may match' },
	{ value: 'not', detail: 'Exclude what follows' }
];
const RELATIVE_DATES = [
	{ value: '<24h', detail: 'Within the last day' },
	{ value: '<7d', detail: 'Within the last week' },
	{ value: '<30d', detail: 'Within the last month' },
	{ value: '>90d', detail: 'Older than three months' }
];
const FUTURE_DATES = [
	{ value: '<7d', detail: 'Inside a week' },
	{ value: '<30d', detail: 'Inside a month' },
	{ value: '<90d', detail: 'Inside three months' },
	{ value: '>1y', detail: 'More than a year out' }
];
const NUMERIC_TEMPLATES = [
	{ value: '>', detail: 'Greater than' },
	{ value: '<', detail: 'Less than' },
	{ value: '>=', detail: 'At least' },
	{ value: '<=', detail: 'At most' }
];

function matches(candidate: string, prefix: string): boolean {
	return !prefix || candidate.toLowerCase().includes(prefix.toLowerCase());
}

function describes(description: string, prefix: string): boolean {
	return description
		.toLowerCase()
		.split(/[^a-z0-9.]+/)
		.some((word) => word.startsWith(prefix));
}

function fieldSuggestions(schema: QuerySchema, prefix: string): Suggestion[] {
	const lowered = prefix.toLowerCase();
	const scored = schema.fields
		.map((field) => {
			const names = [field.name, ...field.aliases];
			const hit = names.find((n) => n.startsWith(lowered));
			const loose = names.find((n) => n.includes(lowered));
			if (!lowered) return { field, rank: 1, name: field.name };
			if (hit) return { field, rank: 0, name: hit };
			if (loose) return { field, rank: 2, name: field.name };
			return describes(field.description, lowered) ? { field, rank: 3, name: field.name } : null;
		})
		.filter((v): v is { field: QueryFieldSpec; rank: number; name: string } => v !== null)
		.sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name));

	return scored.slice(0, 10).map(({ field, name }) => ({
		id: `field:${field.name}`,
		insert: `${name}:`,
		label: `${name}:`,
		detail: field.description,
		hint: field.type,
		group: field.group,
		keepOpen: true
	}));
}

function connectorSuggestions(prefix: string): Suggestion[] {
	if (!prefix) return [];
	return CONNECTOR_SUGGESTIONS.filter((c) => c.value.startsWith(prefix.toLowerCase())).map((c) => ({
		id: `connector:${c.value}`,
		insert: `${c.value} `,
		label: c.value,
		detail: c.detail,
		group: 'Logic'
	}));
}

function optionsFor(
	field: QueryFieldSpec,
	schema: QuerySchema,
	facets: Record<string, Facet[]>
): { value: string; detail?: string; hint?: string }[] {
	if (field.name === 'is') {
		return schema.flags.map((f) => ({ value: f.value, detail: f.description }));
	}
	if (field.facet) {
		return (facets[field.facet] ?? []).map((f) => ({
			value: f.value,
			detail: f.label !== f.value ? f.label : undefined,
			hint: f.count ? f.count.toLocaleString() : undefined
		}));
	}
	if (field.values.length) return field.values.map((v) => ({ value: v }));
	if (field.type === 'date') {
		return (field.name === 'cert.expires' ? FUTURE_DATES : RELATIVE_DATES).map((d) => ({
			value: d.value,
			detail: d.detail
		}));
	}
	if (field.type === 'number' || field.type === 'bytes' || field.type === 'duration') {
		return NUMERIC_TEMPLATES.map((t) => ({ value: t.value, detail: t.detail }));
	}
	return [];
}

function valueSuggestions(
	context: Extract<CaretContext, { kind: 'value' }>,
	schema: QuerySchema,
	facets: Record<string, Facet[]>,
	byName: Map<string, QueryFieldSpec>
): Suggestion[] {
	const field = byName.get(context.field);
	if (!field) return [];
	const bare = context.prefix.replace(/^[!><=~]+/, '');
	const options = optionsFor(field, schema, facets)
		.filter((o) => matches(o.value, bare) && o.value.toLowerCase() !== bare.toLowerCase())
		.slice(0, MAX_PER_GROUP);
	return options.map((option) => ({
		id: `value:${field.name}:${option.value}`,
		insert: /^[!><=~]/.test(option.value) ? option.value : `${quoteValue(option.value)} `,
		label: option.value,
		detail: option.detail,
		hint: option.hint,
		group: field.name
	}));
}

export function buildSuggestions(
	context: CaretContext | null,
	schema: QuerySchema,
	facets: Record<string, Facet[]>,
	byName: Map<string, QueryFieldSpec>
): Suggestion[] {
	if (!context || !schema.fields.length) return [];
	if (context.kind === 'value') return valueSuggestions(context, schema, facets, byName);
	return [...connectorSuggestions(context.prefix), ...fieldSuggestions(schema, context.prefix)];
}
