/** A results table's sort: the column key and its direction, 1 ascending, -1 descending. */
export interface SortKey {
	key: string;
	dir: 1 | -1;
}

/** Reads a `key:asc` / `key:desc` URL value; anything without a key falls back. */
export function parseSort(raw: string | null | undefined, fallback: SortKey): SortKey {
	const [key, dir] = raw?.split(':') ?? [];
	return key ? { key, dir: dir === 'desc' ? -1 : 1 } : { ...fallback };
}

/** The URL value for a sort, or null when it is the table's default and needs no param. */
export function sortParam(sort: SortKey, fallback: SortKey): string | null {
	if (sort.key === fallback.key && sort.dir === fallback.dir) return null;
	return `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`;
}

/** Clicking the sorted column flips it; clicking another sorts that one in the `first` direction. */
export function flipSort(sort: SortKey, key: string, first: 1 | -1 = 1): SortKey {
	return sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: first };
}

/** Zero-based page index from a one-based `page` URL value; a malformed value reads as page one. */
export function parsePageIndex(raw: string | null | undefined): number {
	const page = Math.floor(Number(raw ?? 1));
	return Number.isFinite(page) ? Math.max(0, page - 1) : 0;
}

/** The URL value for a zero-based page index, or null on the first page. */
export function pageParam(pageIndex: number): string | null {
	return pageIndex > 0 ? String(pageIndex + 1) : null;
}

/** Reads a URL param, falling back to older spellings so links shared before a rename keep working. */
export function readParam(
	params: URLSearchParams,
	key: string,
	...legacy: string[]
): string | null {
	for (const name of [key, ...legacy]) {
		const value = params.get(name);
		if (value !== null) return value;
	}
	return null;
}
