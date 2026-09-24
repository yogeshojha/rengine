import { STORAGE_KEYS } from '$lib/config/storage-keys';

export const FINDING_COLUMNS = ['asset', 'related', 'risk', 'evidence', 'review', 'seen'] as const;
export type FindingColumn = (typeof FINDING_COLUMNS)[number];
export const FINDING_COLUMN_LABELS: Record<FindingColumn, string> = {
	asset: 'Web asset',
	related: 'Correlation',
	risk: 'Risk',
	evidence: 'Evidence',
	review: 'Review',
	seen: 'Seen'
};

export const BRIEF_TABS = ['asset', 'host', 'check', 'evidence', 'intel'] as const;
export type BriefTab = (typeof BRIEF_TABS)[number];
export const BRIEF_TAB_LABELS: Record<BriefTab, string> = {
	asset: 'Web asset',
	host: 'On this asset',
	check: 'Same check',
	evidence: 'Evidence',
	intel: 'Intel'
};

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

function createFindingPrefs() {
	let hidden = $state<FindingColumn[]>(
		(read(STORAGE_KEYS.vulnsHidden) ?? '')
			.split(',')
			.filter((c): c is FindingColumn => (FINDING_COLUMNS as readonly string[]).includes(c))
	);
	let tab = $state<BriefTab>(
		(BRIEF_TABS as readonly string[]).includes(read(STORAGE_KEYS.vulnsBriefTab) ?? '')
			? (read(STORAGE_KEYS.vulnsBriefTab) as BriefTab)
			: 'asset'
	);

	let summary = $state(read(STORAGE_KEYS.vulnsSummary) !== 'collapsed');

	return {
		get summary() {
			return summary;
		},
		set summary(v: boolean) {
			summary = v;
			write(STORAGE_KEYS.vulnsSummary, v ? 'open' : 'collapsed');
		},
		get tab() {
			return tab;
		},
		set tab(v: BriefTab) {
			tab = v;
			write(STORAGE_KEYS.vulnsBriefTab, v);
		},
		shows(col: FindingColumn) {
			return !hidden.includes(col);
		},
		toggle(col: FindingColumn) {
			hidden = hidden.includes(col) ? hidden.filter((c) => c !== col) : [...hidden, col];
			write(STORAGE_KEYS.vulnsHidden, hidden.join(','));
		}
	};
}

export const findingPrefs = createFindingPrefs();
