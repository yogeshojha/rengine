import { describe, expect, it } from 'vitest';
import {
	ACCESS_KEY_LEVELS,
	ACCESS_KEY_PREFIX,
	AccessKeyLevel,
	DEFAULT_EXPIRY_DAYS,
	EXPIRY_DAYS,
	EXPIRY_LABELS,
	LEVEL_HELP,
	LEVEL_LABELS,
	LIMIT_DETAIL,
	MAX_ACCESS_KEYS,
	MAX_NAME_LENGTH,
	expiryDays,
	expiryValue
} from './access-keys';
import { EXAMPLE_BASE_URL, EXAMPLE_KEY_VARIABLE, PROJECT_VARIABLE } from './api-reference';

describe('access key vocabulary', () => {
	it('matches shared/definitions/access_keys.py', () => {
		expect(ACCESS_KEY_PREFIX).toBe('rngkey_');
		expect(MAX_ACCESS_KEYS).toBe(20);
		expect(MAX_NAME_LENGTH).toBe(80);
		expect(Object.values(AccessKeyLevel)).toEqual(['read', 'write']);
		expect(LEVEL_LABELS).toEqual({ read: 'Read', write: 'Read and write' });
		expect(LEVEL_HELP).toEqual({
			read: 'Search, list, export and compare.',
			write: 'Also targets, scans, triage and notes.'
		});
		expect(EXPIRY_DAYS).toEqual([30, 90, 365, null]);
		expect(DEFAULT_EXPIRY_DAYS).toBe(90);
		expect(LIMIT_DETAIL).toBe('An account holds at most 20 access keys.');
		expect(EXAMPLE_BASE_URL).toBe('https://rengine.example.com');
		expect(EXAMPLE_KEY_VARIABLE).toBe('RENGINE_KEY');
		expect(PROJECT_VARIABLE).toBe('$PROJECT_ID');
	});

	it('labels every expiry choice and no other', () => {
		expect([...EXPIRY_LABELS.keys()]).toEqual([...EXPIRY_DAYS]);
		expect([...EXPIRY_LABELS.values()]).toEqual(['30 days', '90 days', '1 year', 'No expiry']);
		expect(EXPIRY_DAYS).toContain(DEFAULT_EXPIRY_DAYS);
	});

	it('lists both levels', () => {
		expect(ACCESS_KEY_LEVELS).toEqual(Object.values(AccessKeyLevel));
	});

	it('round-trips an expiry through its form value', () => {
		for (const days of EXPIRY_DAYS) expect(expiryDays(expiryValue(days))).toBe(days);
		expect(expiryValue(null)).toBe('never');
	});
});
