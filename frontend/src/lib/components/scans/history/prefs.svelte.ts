import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { Severity } from '$lib/config/vulnerabilities';

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

export type Density = 'comfortable' | 'compact';

const SIGNAL = [Severity.CRITICAL, Severity.HIGH] as const;
export const STRIP_SEVERITIES: string[] = [...SIGNAL, Severity.MEDIUM];

function read(key: string): string | null {
	try {
		return localStorage.getItem(key);
	} catch {
		return null;
	}
}

function write(key: string, value: string) {
	try {
		localStorage.setItem(key, value);
	} catch {
		/* storage unavailable */
	}
}

function createHistoryPrefs() {
	let showMedium = $state(read(STORAGE_KEYS.scansShowMedium) === '1');
	let hidden = $state<HistoryColumn[]>(
		(read(STORAGE_KEYS.scansColumns) ?? '')
			.split(',')
			.filter((c): c is HistoryColumn => (HISTORY_COLUMNS as readonly string[]).includes(c))
	);
	let density = $state<Density>(
		read(STORAGE_KEYS.scansDensity) === 'compact' ? 'compact' : 'comfortable'
	);
	let tab = $state<BriefTab>(
		(BRIEF_TABS as readonly string[]).includes(read(STORAGE_KEYS.scansBriefTab) ?? '')
			? (read(STORAGE_KEYS.scansBriefTab) as BriefTab)
			: 'findings'
	);

	const severities = $derived<string[]>(showMedium ? [...SIGNAL, Severity.MEDIUM] : [...SIGNAL]);

	return {
		get showMedium() {
			return showMedium;
		},
		set showMedium(v: boolean) {
			showMedium = v;
			write(STORAGE_KEYS.scansShowMedium, v ? '1' : '0');
		},
		get severities() {
			return severities;
		},
		get density() {
			return density;
		},
		set density(v: Density) {
			density = v;
			write(STORAGE_KEYS.scansDensity, v);
		},
		get tab() {
			return tab;
		},
		set tab(v: BriefTab) {
			tab = v;
			write(STORAGE_KEYS.scansBriefTab, v);
		},
		shows(col: HistoryColumn) {
			return !hidden.includes(col);
		},
		toggle(col: HistoryColumn) {
			hidden = hidden.includes(col) ? hidden.filter((c) => c !== col) : [...hidden, col];
			write(STORAGE_KEYS.scansColumns, hidden.join(','));
		}
	};
}

export const historyPrefs = createHistoryPrefs();
