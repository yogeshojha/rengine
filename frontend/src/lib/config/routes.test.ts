import { describe, expect, it } from 'vitest';
import { needsProject } from './routes';

describe('needsProject', () => {
	it('holds for project pages', () => {
		expect(needsProject('/dashboard')).toBe(true);
		expect(needsProject('/targets/123')).toBe(true);
		expect(needsProject('/settingsx')).toBe(true);
	});

	it('leaves instance pages out', () => {
		expect(needsProject('/settings')).toBe(false);
		expect(needsProject('/settings/users')).toBe(false);
		expect(needsProject('/profile')).toBe(false);
		expect(needsProject('/arsenal')).toBe(false);
		expect(needsProject('/bounty-hub/hackerone')).toBe(false);
	});
});
