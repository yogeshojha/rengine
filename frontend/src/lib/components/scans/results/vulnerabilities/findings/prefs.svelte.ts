import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { briefTabs } from '$lib/utilities/brief-tabs.svelte';
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

export const SHEET_TABS = ['overview', 'ask', 'evidence', 'related', 'intel'] as const;
export type SheetTab = (typeof SHEET_TABS)[number];
export const SHEET_TAB_LABELS: Record<SheetTab, string> = {
	overview: 'Overview',
	ask: 'Ask',
	evidence: 'Evidence',
	related: 'Same check',
	intel: 'Intel'
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

export const findingBriefTabs = briefTabs<BriefTab>(BRIEF_TABS[0]);

function createFindingPrefs() {
	let hidden = $state<FindingColumn[]>(
		(readStored(STORAGE_KEYS.vulnsHidden) ?? '')
			.split(',')
			.filter((c): c is FindingColumn => (FINDING_COLUMNS as readonly string[]).includes(c))
	);
	let summary = $state(readStored(STORAGE_KEYS.vulnsSummary) !== 'collapsed');

	return {
		get summary() {
			return summary;
		},
		set summary(v: boolean) {
			summary = v;
			writeStored(STORAGE_KEYS.vulnsSummary, v ? 'open' : 'collapsed');
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
