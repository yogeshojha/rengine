import { browser } from '$app/environment';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { localPath } from '$lib/utilities/links';
import type { Crumb } from './breadcrumbs.svelte';

const KEY = STORAGE_KEYS.previousPage;
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

/** The page each page was opened from, by pathname, for the tab's session. */
export const previousPage = {
	record(pathname: string, from: Crumb) {
		delete entries[pathname];
		entries[pathname] = from;
		const keys = Object.keys(entries);
		for (const key of keys.slice(0, Math.max(0, keys.length - KEEP))) delete entries[key];
		try {
			sessionStorage.setItem(KEY, JSON.stringify(entries));
		} catch {
			// storage off or full
		}
	},

	of(pathname: string): Crumb | undefined {
		const crumb = entries[pathname];
		const href = localPath(crumb?.href);
		return crumb && href ? { ...crumb, href } : undefined;
	},

	clear() {
		for (const key of Object.keys(entries)) delete entries[key];
		try {
			sessionStorage.removeItem(KEY);
		} catch {
			// storage off
		}
	}
};
