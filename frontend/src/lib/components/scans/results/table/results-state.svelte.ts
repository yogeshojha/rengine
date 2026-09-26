import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
import { afterPause } from '$lib/utilities/debounce';
import { LatestRequest } from '$lib/utilities/latest-request';
import { RESULTS_PAGE_SIZE } from '$lib/utilities/scan-status';
import { readPref, writePref } from '$lib/utilities/storage';
import { flipSort, type SortKey } from './sort';

/** The page of rows every results search endpoint answers with. */
export interface SearchPage<T> {
	items: T[];
	total: number;
	total_capped: boolean;
	error: QueryError | null;
}

export interface ResultsTableInit<F> {
	/** Facets shown before the first facet load lands. */
	facets: F;
	sort: SortKey;
	pageIndex: number;
	/** localStorage key the page size persists under. */
	pageSizeKey: string;
	/** localStorage key the row density persists under; a table without a density picker omits it. */
	densityKey?: string;
}

/**
 * The state every scan-results table carries: the current page of rows, the search that
 * produced it, facets, the lead set, sort, paging and density. Construct it during component
 * init: the page size and density persist through effects the constructor registers.
 */
export class ResultsTable<T, F> {
	items = $state<T[]>([]);
	total = $state(0);
	totalCapped = $state(false);
	queryError = $state<QueryError | null>(null);
	queryReady = $state(true);
	loading = $state(true);
	refreshing = $state(false);
	errored = $state(false);
	facets = $state<F>() as F;
	facetsLoaded = $state(false);
	leadSet = $state<QueryLeads | null>(null);
	sort = $state<SortKey>({ key: '', dir: 1 });
	pageIndex = $state(0);
	pageSize = $state(RESULTS_PAGE_SIZE);
	density = $state('cozy');

	readonly pageCount = $derived(Math.max(1, Math.ceil(this.total / this.pageSize)));

	/** Guards the row search, so a slow answer to an older query never overwrites a newer one. */
	readonly searchRequest = new LatestRequest();

	constructor(init: ResultsTableInit<F>) {
		this.facets = init.facets;
		this.sort = init.sort;
		this.pageIndex = init.pageIndex;
		this.pageSize = readPref(init.pageSizeKey, RESULTS_PAGE_SIZE);
		$effect(() => writePref(init.pageSizeKey, this.pageSize));
		const densityKey = init.densityKey;
		if (densityKey) {
			this.density = readPref(densityKey, 'cozy');
			$effect(() => writePref(densityKey, this.density));
		}
	}

	/** Takes a search answer as the current page. */
	accept(res: SearchPage<T>): void {
		this.items = res.items;
		this.total = res.total;
		this.totalCapped = res.total_capped;
		this.queryError = res.error;
		this.errored = false;
	}

	/** Empties the page after a search that did not answer. */
	fail(): void {
		this.items = [];
		this.total = 0;
		this.totalCapped = false;
		this.errored = true;
	}

	/**
	 * Sorts by `key`, flipping the direction when it is already the sort, and returns to page one.
	 * A newly picked column starts in the `first` direction.
	 */
	toggleSort(key: string, first: 1 | -1 = 1): void {
		this.sort = flipSort(this.sort, key, first);
		this.pageIndex = 0;
	}

	/** Changes the page size and returns to page one. */
	setPageSize(size: number): void {
		this.pageSize = size;
		this.pageIndex = 0;
	}
}

/** A slot filled by the newest of its loads; an older response that lands late is dropped. */
export class LatestLoad<S> {
	value = $state<S | null>(null);
	failed = $state(false);
	loading = $state(false);

	#req = new LatestRequest();

	async load(fetch: () => Promise<S>): Promise<void> {
		this.loading = true;
		// a retry shows as loading, not as the last attempt's failure
		this.failed = false;
		await this.#req.run(fetch, {
			done: (res) => {
				this.value = res;
				this.failed = false;
			},
			failed: () => {
				this.value = null;
				this.failed = true;
			},
			settled: () => {
				this.loading = false;
			}
		});
	}
}

/** The group-by view of a results table: the dimension picked and the buckets it produced. */
export class GroupedView extends LatestLoad<QueryGroups> {
	by = $state('');

	#fetch: (by: string) => Promise<QueryGroups>;
	#ready: () => boolean;

	/**
	 * @param by the dimension to start grouped by, '' for none
	 * @param fetch loads the buckets for a dimension under the table's current query
	 * @param ready whether the table has what it needs to query (a project, and a scan when scoped)
	 */
	constructor(by: string, fetch: (by: string) => Promise<QueryGroups>, ready: () => boolean) {
		super();
		this.by = by;
		this.#fetch = fetch;
		this.#ready = ready;
	}

	/** Loads the buckets for the current dimension; with none picked, drops the last set. */
	reload = async (): Promise<void> => {
		if (!this.by || !this.#ready()) {
			this.value = null;
			return;
		}
		const by = this.by;
		await this.load(() => this.#fetch(by));
	};

	/** For an effect: reloads after the search pause and returns the cleanup that cancels it. */
	schedule(): (() => void) | undefined {
		if (!this.by) {
			this.value = null;
			return undefined;
		}
		return afterPause(this.reload);
	}
}
