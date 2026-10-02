import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { readStored, writeStored } from '$lib/utilities/storage';

export const FINDING_COLUMNS = [
	'asset',
	'related',
	'risk',
	'evidence',
	'review',
	'issue',
	'seen'
] as const;
export type FindingColumn = (typeof FINDING_COLUMNS)[number];
export const FINDING_COLUMN_LABELS: Record<FindingColumn, string> = {
	asset: 'Web asset',
	related: 'Related findings',
	risk: 'Risk',
	evidence: 'Evidence',
	review: 'Review',
	issue: 'Issue',
	seen: 'Seen'
};

export const SHEET_TABS = ['overview', 'evidence', 'related', 'intel', 'notes', 'ask'] as const;
export type SheetTab = (typeof SHEET_TABS)[number];
export const SHEET_TAB_LABELS: Record<SheetTab, string> = {
	overview: 'Overview',
	evidence: 'Evidence',
	related: 'Same check',
	intel: 'Intel',
	notes: 'Notes',
	ask: 'Ask'
};

export const BRIEF_TABS = ['asset', 'host', 'check', 'evidence', 'intel'] as const;
export type BriefTab = (typeof BRIEF_TABS)[number];
export const BRIEF_TAB_LABELS: Record<BriefTab, string> = {
	asset: 'Web asset',
	host: 'Same web asset',
	check: 'Same check',
	evidence: 'Evidence',
	intel: 'Intel'
};

function createFindingPrefs() {
	let hidden = $state<FindingColumn[]>(
		(readStored(STORAGE_KEYS.vulnsHidden) ?? '')
			.split(',')
			.filter((c): c is FindingColumn => (FINDING_COLUMNS as readonly string[]).includes(c))
	);
	let tab = $state<BriefTab>(
		(BRIEF_TABS as readonly string[]).includes(readStored(STORAGE_KEYS.vulnsBriefTab) ?? '')
			? (readStored(STORAGE_KEYS.vulnsBriefTab) as BriefTab)
			: 'asset'
	);

	let sheetTab = $state<SheetTab>(
		(SHEET_TABS as readonly string[]).includes(readStored(STORAGE_KEYS.vulnsSheetTab) ?? '')
			? (readStored(STORAGE_KEYS.vulnsSheetTab) as SheetTab)
			: 'overview'
	);
	let summary = $state(readStored(STORAGE_KEYS.vulnsSummary) !== 'collapsed');

	return {
		get sheetTab() {
			return sheetTab;
		},
		set sheetTab(v: SheetTab) {
			sheetTab = v;
			writeStored(STORAGE_KEYS.vulnsSheetTab, v);
		},
		get summary() {
			return summary;
		},
		set summary(v: boolean) {
			summary = v;
			writeStored(STORAGE_KEYS.vulnsSummary, v ? 'open' : 'collapsed');
		},
		get tab() {
			return tab;
		},
		set tab(v: BriefTab) {
			tab = v;
			writeStored(STORAGE_KEYS.vulnsBriefTab, v);
		},
		shows(col: FindingColumn) {
			return !hidden.includes(col);
		},
		toggle(col: FindingColumn) {
			hidden = hidden.includes(col) ? hidden.filter((c) => c !== col) : [...hidden, col];
			writeStored(STORAGE_KEYS.vulnsHidden, hidden.join(','));
		}
	};
}

export const findingPrefs = createFindingPrefs();
