import { STORAGE_KEYS } from '$lib/config/storage-keys';

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

export type Density = 'comfortable' | 'compact';

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

function createTargetPrefs() {
	let hidden = $state<TargetColumn[]>(
		(read(STORAGE_KEYS.targetsHidden) ?? '')
			.split(',')
			.filter((c): c is TargetColumn => (TARGET_COLUMNS as readonly string[]).includes(c))
	);
	let density = $state<Density>(
		read(STORAGE_KEYS.targetsDensity) === 'compact' ? 'compact' : 'comfortable'
	);

	return {
		get density() {
			return density;
		},
		set density(v: Density) {
			density = v;
			write(STORAGE_KEYS.targetsDensity, v);
		},
		shows(col: TargetColumn) {
			return !hidden.includes(col);
		},
		toggle(col: TargetColumn) {
			hidden = hidden.includes(col) ? hidden.filter((c) => c !== col) : [...hidden, col];
			write(STORAGE_KEYS.targetsHidden, hidden.join(','));
		}
	};
}

export const targetPrefs = createTargetPrefs();
