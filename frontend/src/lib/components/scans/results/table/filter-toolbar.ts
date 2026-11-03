import {
	hasTopLevelOr,
	holdsClause,
	tokenize,
	withoutClause,
	type Facet
} from '$lib/utilities/scan-insights';

export type FacetOption = Omit<Facet, 'count'> & { count?: number };

/** one multi-value picker in the Filter menu */
export interface FacetSpec {
	key: string;
	label: string;
	options: FacetOption[];
	selected: string[];
	onChange: (next: string[]) => void;
	/** options render in the mono face (hostnames, check ids) */
	mono?: boolean;
	loading?: boolean;
	/** one value at a time */
	single?: boolean;
}

/** one on/off filter in the Filter menu */
export interface SignalSpec {
	key: string;
	label: string;
	on: boolean;
	count?: number | null;
	onToggle: () => void;
	/** a view preference, switched in the menu without a chip */
	quiet?: boolean;
	/** the grammar token the signal stands for */
	token?: string;
}

/** a chip the table owns outside the facets and signals */
export interface ExtraChip {
	id: string;
	label: string;
	mono?: boolean;
	onRemove: () => void;
}

/** a counted query the table can apply in one click */
export interface FilterSuggestion {
	query: string;
	description: string;
	/** rows the click opens, when known for this view */
	count: number | null;
	capped: boolean;
}

export interface ToolbarChip {
	id: string;
	label: string;
	values: string[];
	mono: boolean;
	facet: string | null;
	onRemove: () => void;
}

export const SHOWN_VALUES = 2;
export const SUGGESTIONS_SHOWN = 5;
export const MAX_CHIP_QUERY = 44;
/** query characters the suggestion chips may fill on one row */
export const SUGGESTION_CHARS = 100;
export const MENU_SUGGESTIONS = 6;
export const SUGGESTIONS_WITH_CHIPS = 3;

/** the chip rows a set of facets, signals and extras produces */
export function toolbarChips(
	facets: FacetSpec[],
	signals: SignalSpec[],
	extras: ExtraChip[]
): ToolbarChip[] {
	const chips: ToolbarChip[] = [];
	for (const facet of facets) {
		if (!facet.selected.length) continue;
		const labels = new Map(facet.options.map((o) => [o.value, o.label]));
		chips.push({
			id: `facet:${facet.key}`,
			label: facet.label,
			values: facet.selected.map((v) => labels.get(v) ?? v),
			mono: facet.mono ?? false,
			facet: facet.key,
			onRemove: () => facet.onChange([])
		});
	}
	const signalTokens = new Set(signals.filter((s) => s.on && s.token).map((s) => s.token));
	const queries = extras.filter((e) => e.mono && !signalTokens.has(e.label));
	const queryTokens = new Set(queries.flatMap((e) => e.label.split(/\s+/)));
	for (const signal of signals) {
		if (!signal.on || signal.quiet) continue;
		if (signal.token && queryTokens.has(signal.token)) continue;
		chips.push({
			id: `signal:${signal.key}`,
			label: signal.label,
			values: [],
			mono: false,
			facet: null,
			onRemove: signal.onToggle
		});
	}
	for (const extra of extras) {
		if (extra.mono && signalTokens.has(extra.label)) continue;
		chips.push({
			id: `extra:${extra.id}`,
			label: extra.label,
			values: [],
			mono: extra.mono ?? false,
			facet: null,
			onRemove: extra.onRemove
		});
	}
	return chips;
}

export function valuesLabel(values: string[]): string {
	if (values.length <= SHOWN_VALUES) return values.join(', ');
	return `${values.slice(0, SHOWN_VALUES).join(', ')} +${values.length - SHOWN_VALUES}`;
}

export const escapeRe = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** the lead as one clause: parenthesised when it carries a top-level or */
export function clauseOf(query: string): string {
	return hasTopLevelOr(tokenize(query)) ? `(${query})` : query;
}

/** the lead joined onto the search with and */
export function joinSuggestion(search: string, query: string): string {
	const base = search.trim();
	if (!base) return query;
	const left = hasTopLevelOr(tokenize(base)) ? `(${base})` : base;
	return `${left} and ${clauseOf(query)}`;
}

export function holdsSuggestion(search: string, query: string): boolean {
	return holdsClause(search, clauseOf(query)) || holdsClause(search, query);
}

export function dropSuggestion(search: string, query: string): string {
	const clause = clauseOf(query);
	return holdsClause(search, clause) ? withoutClause(search, clause) : withoutClause(search, query);
}
