import { browser } from '$app/environment';
import { SvelteSet } from 'svelte/reactivity';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { readPref, writePref } from '$lib/utilities/storage';
import { PINNED_SCAN_TABS, type ScanTab } from '$lib/config/scan-tabs';

interface Stored {
	hidden: string[];
	shown: string[];
}

function read(): Stored {
	if (!browser) return { hidden: [], shown: [] };
	const parsed = readPref<Partial<Stored> | null>(STORAGE_KEYS.scanTabs, null);
	return {
		hidden: Array.isArray(parsed?.hidden) ? parsed.hidden : [],
		shown: Array.isArray(parsed?.shown) ? parsed.shown : []
	};
}

function createScanTabs() {
	const stored = read();
	const hidden = new SvelteSet(stored.hidden);
	const shown = new SvelteSet(stored.shown);

	function persist() {
		if (!browser) return;
		writePref(STORAGE_KEYS.scanTabs, { hidden: [...hidden], shown: [...shown] });
	}

	return {
		visible(key: ScanTab, defaultOn: boolean): boolean {
			if (PINNED_SCAN_TABS.includes(key)) return true;
			if (hidden.has(key)) return false;
			if (shown.has(key)) return true;
			return defaultOn;
		},
		show(key: ScanTab) {
			hidden.delete(key);
			shown.add(key);
			persist();
		},
		hide(key: ScanTab) {
			if (PINNED_SCAN_TABS.includes(key)) return;
			shown.delete(key);
			hidden.add(key);
			persist();
		},
		reset() {
			hidden.clear();
			shown.clear();
			persist();
		},
		get customized(): boolean {
			return hidden.size > 0 || shown.size > 0;
		}
	};
}

export const scanTabs = createScanTabs();
