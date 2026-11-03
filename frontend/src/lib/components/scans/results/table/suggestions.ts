import type { TabCounts } from '$lib/utilities/tab-counts.svelte';
import { appendToken, holdsClause, withoutToken } from '$lib/utilities/scan-insights';
import {
	dropSuggestion,
	escapeRe,
	holdsSuggestion,
	joinSuggestion,
	type ExtraChip,
	type FilterSuggestion,
	type SignalSpec
} from './filter-toolbar';

export const SUGGESTION_CANDIDATES = 8;
export const NEW_TOKEN = 'is:new';

/** a query the table can suggest, counted when the source counts it */
export interface SuggestionSource {
	query: string;
	description: string;
	count?: number;
	capped?: boolean;
}

export function holdsNew(search: string): boolean {
	return holdsClause(search, NEW_TOKEN);
}

/** the search with the is:new token added or removed */
export function withNew(search: string, on: boolean): string {
	return on ? appendToken(search, NEW_TOKEN) : withoutToken(search, NEW_TOKEN);
}

/** the New signal every table offers, on while the search holds is:new */
export function newSignal(
	search: string,
	onSearch: (next: string) => void,
	alsoOn = false
): SignalSpec {
	const on = alsoOn || holdsNew(search);
	return {
		key: 'new',
		label: 'New',
		token: NEW_TOKEN,
		on,
		onToggle: () => onSearch(withNew(search, !on))
	};
}

/** a query shape and whether the table already filters on it */
export type OverlapRule = [RegExp, boolean];

/** the rule for a token the table switches on and off */
export function tokenRule(token: string, on: boolean): OverlapRule {
	return [new RegExp(`(^|\\s)${escapeRe(token)}(\\s|$)`), on];
}

export function overlaps(rules: OverlapRule[]): (query: string) => boolean {
	return (query) => rules.some(([re, on]) => on && re.test(query));
}

/** the leads a click could still narrow the view with */
export function suggestionCandidates(
	leads: SuggestionSource[],
	search: string,
	overlapping: (query: string) => boolean,
	total: number | null
): SuggestionSource[] {
	return leads
		.filter((lead) => lead.count == null || lead.count > 0)
		.filter((lead) => !holdsSuggestion(search, lead.query))
		.filter((lead) => !overlapping(lead.query))
		.filter((lead) => lead.count == null || total == null || lead.count < total)
		.slice(0, SUGGESTION_CANDIDATES);
}

/** the leads the search already carries, as removable chips */
export function appliedLeadChips(
	leads: SuggestionSource[],
	search: string,
	onSearch: (next: string) => void
): ExtraChip[] {
	return leads
		.filter((lead) => holdsSuggestion(search, lead.query))
		.map((lead) => ({
			id: `lead:${lead.query}`,
			label: lead.query,
			mono: true,
			onRemove: () => onSearch(dropSuggestion(search, lead.query))
		}));
}

/** the search with every applied lead removed */
export function clearLeadSearch(leads: SuggestionSource[], search: string): string {
	return leads.reduce((acc, lead) => dropSuggestion(acc, lead.query), search);
}

export function suggestionQueries(candidates: SuggestionSource[], search: string): string[] {
	return candidates.map((lead) => joinSuggestion(search, lead.query));
}

/** the candidates with the counts known for this view, none equal to the view */
export function countedSuggestions(
	candidates: SuggestionSource[],
	search: string,
	exact: boolean,
	counts: Pick<TabCounts, 'counts' | 'capped'>,
	total: number | null
): FilterSuggestion[] {
	const typed = Boolean(search.trim());
	return candidates
		.map((lead) => {
			const joined = joinSuggestion(search, lead.query);
			const own = !typed && lead.count != null;
			const count = own ? (lead.count ?? null) : exact ? (counts.counts?.[joined] ?? null) : null;
			const capped = own ? Boolean(lead.capped) : Boolean(counts.capped?.[joined]);
			return { query: lead.query, description: lead.description, count, capped };
		})
		.filter((s) => s.count !== 0 && (s.count == null || total == null || s.count < total));
}
