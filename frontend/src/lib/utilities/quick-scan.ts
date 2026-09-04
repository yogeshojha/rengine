import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { SELECT_NONE } from '$lib/constants';
import type { ScanEngine } from '$lib/types/scan-engine';

export interface QuickScanPrefs {
	enabled: boolean;
	engineId: string;
	contextId: string;
}

export function pickDefaultEngine(engines: ScanEngine[]): string {
	if (engines.length === 0) return '';
	const used = engines.filter((e) => e.last_used_at);
	if (used.length === 0) return engines[0].id;
	return used.reduce((a, b) =>
		new Date(a.last_used_at as string) >= new Date(b.last_used_at as string) ? a : b
	).id;
}

export function readQuickScanPrefs(storageKey: string): QuickScanPrefs {
	if (typeof localStorage === 'undefined')
		return { enabled: false, engineId: '', contextId: SELECT_NONE };
	return {
		enabled: localStorage.getItem(storageKey) === '1',
		engineId: localStorage.getItem(STORAGE_KEYS.launchLastEngine) ?? '',
		contextId: localStorage.getItem(STORAGE_KEYS.launchLastContext) ?? SELECT_NONE
	};
}

export function rememberQuickScanToggle(storageKey: string, enabled: boolean) {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(storageKey, enabled ? '1' : '0');
}

export function rememberQuickScanChoice(engineId: string, contextId: string) {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(STORAGE_KEYS.launchLastEngine, engineId);
	localStorage.setItem(STORAGE_KEYS.launchLastContext, contextId);
}
