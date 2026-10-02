import type { QueryCounts } from '$lib/types/asset-query';
import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

type Loader = () => Promise<QueryCounts>;

export const ALL_TAB = 'all';

/** The query a grammar tab opens: the search without the field, then the tab's value. */
export function withTab(search: string, field: string, key: string): string {
	const without = search.replace(new RegExp(`(?:^|\\s)${field}:[a-z]+`, 'g'), '').trim();
	return key === ALL_TAB ? without : `${without} ${field}:${key}`.trim();
}

/** Counts of each tab's query, keyed by tab. */
export async function countTabs(
	queries: Record<string, string>,
	load: (queries: string[]) => Promise<QueryCounts>
): Promise<QueryCounts> {
	const unique = Object.values(queries).filter((q, i, all) => all.indexOf(q) === i);
	const res = await load(unique);
	const pick = <T>(by: Record<string, T>) =>
		Object.fromEntries(
			Object.entries(queries)
				.filter(([, query]) => query in by)
				.map(([key, query]) => [key, by[query]])
		);
	return { counts: pick(res.counts), capped: pick(res.capped), computed: res.computed };
}

/** Tab counts over a filtered view, loaded once per filter. */
export class TabCounts {
	counts = $state<Record<string, number> | null>(null);
	capped = $state<Record<string, boolean> | null>(null);
	#delay: number;
	#key = '';
	#load: Loader | null = null;
	#req = 0;
	#timer: ReturnType<typeof setTimeout> | null = null;

	constructor(delay: number = SEARCH_DEBOUNCE_MS) {
		this.#delay = delay;
	}

	track(key: string, load: Loader): void {
		if (key === this.#key) return;
		this.#key = key;
		this.#load = load;
		this.counts = null;
		this.capped = null;
		this.#schedule(this.#delay);
	}

	refresh(): void {
		if (this.#load) this.#schedule(0);
	}

	clear(): void {
		this.#cancel();
		this.#req++;
		this.#key = '';
		this.#load = null;
		this.counts = null;
		this.capped = null;
	}

	#cancel(): void {
		if (this.#timer) clearTimeout(this.#timer);
		this.#timer = null;
	}

	#schedule(delay: number): void {
		this.#cancel();
		const my = ++this.#req;
		const load = this.#load;
		if (!load) return;
		this.#timer = setTimeout(() => void this.#run(my, load), delay);
	}

	async #run(my: number, load: Loader): Promise<void> {
		this.#timer = null;
		try {
			const res = await load();
			if (my !== this.#req) return;
			this.counts = res.computed ? res.counts : null;
			this.capped = res.computed ? res.capped : null;
		} catch {
			if (my === this.#req) this.#key = '';
		}
	}
}
