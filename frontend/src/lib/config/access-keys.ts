// mirrors shared/definitions/access_keys.py

export const ACCESS_KEY_PREFIX = 'rngkey_';
export const MAX_ACCESS_KEYS = 20;
export const MAX_NAME_LENGTH = 80;

export enum AccessKeyLevel {
	READ = 'read',
	WRITE = 'write'
}

export const ACCESS_KEY_LEVELS: readonly AccessKeyLevel[] = [
	AccessKeyLevel.READ,
	AccessKeyLevel.WRITE
];

export const LEVEL_LABELS: Record<AccessKeyLevel, string> = {
	[AccessKeyLevel.READ]: 'Read',
	[AccessKeyLevel.WRITE]: 'Read and write'
};

export const LEVEL_HELP: Record<AccessKeyLevel, string> = {
	[AccessKeyLevel.READ]: 'Search, list, export and compare.',
	[AccessKeyLevel.WRITE]: 'Also targets, scans, triage and notes.'
};

export const LEVEL_BADGE: Record<AccessKeyLevel, 'outline' | 'secondary'> = {
	[AccessKeyLevel.READ]: 'outline',
	[AccessKeyLevel.WRITE]: 'secondary'
};

// days; null is no expiry
export const EXPIRY_DAYS: readonly (number | null)[] = [30, 90, 365, null];
export const DEFAULT_EXPIRY_DAYS = 90;

export const EXPIRY_LABELS: ReadonlyMap<number | null, string> = new Map([
	[30, '30 days'],
	[90, '90 days'],
	[365, '1 year'],
	[null, 'No expiry']
]);

const NEVER = 'never';

/** The expiry choice as a form value, `never` for no expiry. */
export const expiryValue = (days: number | null): string => (days === null ? NEVER : String(days));

export const expiryDays = (value: string): number | null =>
	value === NEVER ? null : Number(value);

export const LIMIT_DETAIL = `An account holds at most ${MAX_ACCESS_KEYS} access keys.`;
