import { toast } from 'svelte-sonner';
import type { CrudApi } from '$lib/api/crud';
import type { ActionResult } from '$lib/types/action-result';
import { nowIso } from '$lib/utilities/dates';
import { errorMessage } from '$lib/utilities/errors';

/** A row that carries the outcome of its last connection test. */
export interface TestedRow {
	id: string;
	last_test_at: string | null;
	last_test_ok: boolean | null;
	last_test_message: string | null;
}

/** The toast shown when a call fails without a message of its own. */
export interface CrudCopy {
	notLoaded: string;
	notCreated: string;
	notSaved: string;
	notDeleted: string;
	testFailed: string;
}

/**
 * A reactive list over a `CrudApi`: fetched once, then kept in step with every
 * create, update, delete and test so the settings panels never refetch.
 */
export function createCrudStore<
	Read extends TestedRow,
	Create,
	Update,
	Tested extends ActionResult = ActionResult
>(source: CrudApi<Read, Create, Update, Tested>, copy: CrudCopy) {
	let items = $state<Read[]>([]);
	let isLoading = $state(false);
	let hasFetched = $state(false);

	return {
		get items() {
			return items;
		},
		get isLoading() {
			return isLoading;
		},
		get hasFetched() {
			return hasFetched;
		},

		async fetch() {
			if (isLoading) return;
			isLoading = true;
			try {
				items = await source.list();
				hasFetched = true;
			} catch (e) {
				toast.error(errorMessage(e, copy.notLoaded));
			} finally {
				isLoading = false;
			}
		},

		async create(data: Create): Promise<Read | null> {
			try {
				const created = await source.create(data);
				items = [...items, created];
				return created;
			} catch (e) {
				toast.error(errorMessage(e, copy.notCreated));
				return null;
			}
		},

		async update(id: string, data: Update): Promise<Read | null> {
			try {
				const updated = await source.update(id, data);
				items = items.map((row) => (row.id === id ? updated : row));
				return updated;
			} catch (e) {
				toast.error(errorMessage(e, copy.notSaved));
				return null;
			}
		},

		/** Drops a row the caller already deleted, without a request. */
		drop(id: string): void {
			items = items.filter((row) => row.id !== id);
		},

		async remove(id: string): Promise<boolean> {
			try {
				await source.remove(id);
				items = items.filter((row) => row.id !== id);
				return true;
			} catch (e) {
				toast.error(errorMessage(e, copy.notDeleted));
				return false;
			}
		},

		async test(id: string): Promise<Tested | null> {
			try {
				const result = await source.test(id);
				const testedAt = nowIso();
				items = items.map((row) =>
					row.id === id
						? {
								...row,
								last_test_at: testedAt,
								last_test_ok: result.success,
								last_test_message: result.message
							}
						: row
				);
				return result;
			} catch (e) {
				toast.error(errorMessage(e, copy.testFailed));
				return null;
			}
		},

		/** Rewrites every row, for a server change that also touches siblings. */
		patchAll(fn: (row: Read) => Read): void {
			items = items.map(fn);
		},

		clear() {
			items = [];
			hasFetched = false;
		}
	};
}
