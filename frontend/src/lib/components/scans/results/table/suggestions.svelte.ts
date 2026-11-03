import type { QueryCounts } from '$lib/types/asset-query';
import { TabCounts } from '$lib/utilities/tab-counts.svelte';
import { joinSuggestion, type ExtraChip, type FilterSuggestion } from './filter-toolbar';
import {
	appliedLeadChips,
	clearLeadSearch,
	countedSuggestions,
	suggestionCandidates,
	suggestionQueries,
	type SuggestionSource
} from './suggestions';

export interface SuggestionOptions {
	leads: () => SuggestionSource[];
	search: () => string;
	onSearch: (next: string) => void;
	/** true when a lead would restate a filter the table already applies */
	overlapping?: () => (query: string) => boolean;
	/** rows in the view */
	total: () => number | null;
	/** rows in the scope the leads were counted under */
	leadTotal?: () => number | null;
	/** false while the view counts something other than the rows the leads count */
	countable?: () => boolean;
	ready: () => boolean;
	/** the scan and the facets the counts are read under */
	scope: () => string;
	count: (queries: string[]) => Promise<QueryCounts>;
}

export interface Suggestions {
	readonly list: FilterSuggestion[];
	readonly applied: ExtraChip[];
	apply: (suggestion: FilterSuggestion) => void;
	/** the search with every applied lead removed */
	cleared: () => string;
	refresh: () => void;
}

/** suggested queries for a table, counted where the view's rows are the rows the leads count */
export function createSuggestions(options: SuggestionOptions): Suggestions {
	const counts = new TabCounts();
	const candidates = $derived(
		suggestionCandidates(
			options.leads(),
			options.search(),
			options.overlapping?.() ?? (() => false),
			options.leadTotal?.() ?? null
		)
	);
	const exact = $derived(options.countable?.() ?? true);
	const typed = $derived(Boolean(options.search().trim()));
	const requested = $derived(
		exact && options.ready() && candidates.some((lead) => typed || lead.count == null)
			? suggestionQueries(candidates, options.search())
			: []
	);
	$effect(() => {
		if (!requested.length) {
			counts.clear();
			return;
		}
		const queries = requested;
		counts.track(JSON.stringify([options.scope(), queries]), () => options.count(queries));
	});
	const list = $derived(
		countedSuggestions(candidates, options.search(), exact, counts, options.total())
	);
	const applied = $derived(appliedLeadChips(options.leads(), options.search(), options.onSearch));
	return {
		get list() {
			return list;
		},
		get applied() {
			return applied;
		},
		apply: (suggestion) => options.onSearch(joinSuggestion(options.search(), suggestion.query)),
		cleared: () => clearLeadSearch(options.leads(), options.search()),
		refresh: () => counts.refresh()
	};
}
