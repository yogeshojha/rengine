import { browser } from '$app/environment';
import type { Crumb } from './breadcrumbs.svelte';

const KEY = 'previous-page';
const KEEP = 50;

function load(): Record<string, Crumb> {
	if (!browser) return {};
	try {
		return JSON.parse(sessionStorage.getItem(KEY) ?? '{}') as Record<string, Crumb>;
	} catch {
		return {};
	}
}

const entries = $state<Record<string, Crumb>>(load());

/**
 * The page each page was opened from, by pathname, so a back link can name and return to it.
 * Kept for the tab's session: a reload or a browser Back into the page still knows it.
 */
export const previousPage = {
	record(pathname: string, from: Crumb) {
		delete entries[pathname];
		entries[pathname] = from;
		const keys = Object.keys(entries);
		for (const key of keys.slice(0, Math.max(0, keys.length - KEEP))) delete entries[key];
		try {
			sessionStorage.setItem(KEY, JSON.stringify(entries));
		} catch {
			// storage off or full: the link falls back to the page's parent
		}
	},

	of(pathname: string): Crumb | undefined {
		return entries[pathname];
	}
};
