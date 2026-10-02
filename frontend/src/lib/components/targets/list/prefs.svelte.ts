import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { readStored, writeStored, type Density } from '$lib/utilities/storage';
import { fitColumns } from './columns';

export const TARGET_COLUMNS = [
	'run',
	'findings',
	'assets',
	'change',
	'organizations',
	'tags'
] as const;
export type TargetColumn = (typeof TARGET_COLUMNS)[number];
export const TARGET_COLUMN_LABELS: Record<TargetColumn, string> = {
	run: 'Last run',
	findings: 'Findings',
	assets: 'Assets',
	change: 'Change',
	organizations: 'Organizations',
	tags: 'Tags'
};

function createTargetPrefs() {
	let hidden = $state<TargetColumn[]>(
		(readStored(STORAGE_KEYS.targetsHidden) ?? '')
			.split(',')
			.filter((c): c is TargetColumn => (TARGET_COLUMNS as readonly string[]).includes(c))
	);
	let density = $state<Density>(
		readStored(STORAGE_KEYS.targetsDensity) === 'compact' ? 'compact' : 'comfortable'
	);
	let width = $state(0);
	const fitted = $derived(
		fitColumns(
			width,
			TARGET_COLUMNS.filter((c) => !hidden.includes(c))
		)
	);

	return {
		get density() {
			return density;
		},
		set density(v: Density) {
			density = v;
			writeStored(STORAGE_KEYS.targetsDensity, v);
		},
		get width() {
			return width;
		},
		set width(v: number) {
			width = v;
		},
		shows(col: TargetColumn) {
			return !hidden.includes(col);
		},
		fits(col: TargetColumn) {
			return fitted.has(col);
		},
		folded(col: TargetColumn) {
			return !hidden.includes(col) && !fitted.has(col);
		},
		toggle(col: TargetColumn) {
			hidden = hidden.includes(col) ? hidden.filter((c) => c !== col) : [...hidden, col];
			writeStored(STORAGE_KEYS.targetsHidden, hidden.join(','));
		}
	};
}

export const targetPrefs = createTargetPrefs();
