import type { TabCounts } from '$lib/utilities/tab-counts.svelte';
import { appendToken, tokenize } from '$lib/utilities/scan-insights';
import {
	dropSuggestion,
	holdsSuggestion,
	joinSuggestion,
	type ExtraChip,
	type FilterSuggestion
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

const CONNECTORS = new Set(['and', 'or']);

/** the search without a token, its leading not and any connector left dangling */
export function removeToken(search: string, token: string): string {
	const kept: string[] = [];
	for (const part of tokenize(search)) {
		if (part === token) {
			if (kept.at(-1)?.toLowerCase() === 'not') kept.pop();
			continue;
		}
		kept.push(part);
	}
	const joined: string[] = [];
	for (const part of kept) {
		const connector = CONNECTORS.has(part.toLowerCase());
		if (connector && (!joined.length || CONNECTORS.has(joined.at(-1)!.toLowerCase()))) continue;
		joined.push(part);
	}
	while (joined.length && CONNECTORS.has(joined.at(-1)!.toLowerCase())) joined.pop();
	return joined.join(' ');
}

export function holdsNew(search: string): boolean {
	const parts = tokenize(search);
	const at = parts.indexOf(NEW_TOKEN);
	return at >= 0 && parts[at - 1]?.toLowerCase() !== 'not';
}

/** the search with the is:new token added or removed */
export function withNew(search: string, on: boolean): string {
	return on ? appendToken(search, NEW_TOKEN) : removeToken(search, NEW_TOKEN);
}

/** a query shape and whether the table already filters on it */
export type OverlapRule = [RegExp, boolean];

/** the rule for a token the table switches on and off */
export function tokenRule(token: string, on: boolean): OverlapRule {
	const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	return [new RegExp(`(^|\\s)${escaped}(\\s|$)`), on];
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
