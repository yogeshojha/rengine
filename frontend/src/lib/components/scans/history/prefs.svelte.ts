import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { Severity } from '$lib/config/vulnerabilities';
import { briefTabs } from '$lib/utilities/brief-tabs.svelte';
import { readStored, writeStored, type Density } from '$lib/utilities/storage';

export const HISTORY_COLUMNS = ['assets', 'change', 'engine', 'duration'] as const;
export type HistoryColumn = (typeof HISTORY_COLUMNS)[number];
export const HISTORY_COLUMN_LABELS: Record<HistoryColumn, string> = {
	assets: 'Assets',
	change: 'Change',
	engine: 'Engine',
	duration: 'Duration'
};

export const BRIEF_TABS = ['findings', 'changes', 'coverage', 'engine'] as const;
export type BriefTab = (typeof BRIEF_TABS)[number];
export const BRIEF_TAB_LABELS: Record<BriefTab, string> = {
	findings: 'Findings',
	changes: 'Changes',
	coverage: 'Coverage',
	engine: 'Engine'
};

export const runBriefTabs = briefTabs<BriefTab>(BRIEF_TABS[0]);

const SIGNAL = [Severity.CRITICAL, Severity.HIGH] as const;
export const STRIP_SEVERITIES: string[] = [...SIGNAL, Severity.MEDIUM];

function createHistoryPrefs() {
	let showMedium = $state(readStored(STORAGE_KEYS.scansShowMedium) === '1');
	let hidden = $state<HistoryColumn[]>(
		(readStored(STORAGE_KEYS.scansColumns) ?? '')
			.split(',')
			.filter((c): c is HistoryColumn => (HISTORY_COLUMNS as readonly string[]).includes(c))
	);
	let density = $state<Density>(
		readStored(STORAGE_KEYS.scansDensity) === 'compact' ? 'compact' : 'comfortable'
	);
	const severities = $derived<string[]>(showMedium ? [...SIGNAL, Severity.MEDIUM] : [...SIGNAL]);

	return {
		get showMedium() {
			return showMedium;
		},
		set showMedium(v: boolean) {
			showMedium = v;
			writeStored(STORAGE_KEYS.scansShowMedium, v ? '1' : '0');
		},
		get severities() {
			return severities;
		},
		get density() {
			return density;
		},
		set density(v: Density) {
			density = v;
			writeStored(STORAGE_KEYS.scansDensity, v);
		},
		shows(col: HistoryColumn) {
			return !hidden.includes(col);
		},
		toggle(col: HistoryColumn) {
			hidden = hidden.includes(col) ? hidden.filter((c) => c !== col) : [...hidden, col];
			writeStored(STORAGE_KEYS.scansColumns, hidden.join(','));
		}
	};
}

export const historyPrefs = createHistoryPrefs();
