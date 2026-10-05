import { describe, expect, it } from 'vitest';
import { aboutDetails, checkCount } from './about-details';
import type { About } from '$lib/types/about';

const about: About = {
	version: '3.0.0',
	release_url: 'https://github.com/yogeshojha/rengine/releases/tag/v3.0.0',
	mode: 'bug_bounty',
	architecture: 'x86_64',
	postgres: '16.11',
	redis: null,
	check_library: { version: null, checks: 12864, synced_at: '2026-10-04T12:38:57Z' },
	tools: [
		{ name: 'dnsx', version: 'v1.3.1', url: 'https://example.test/dnsx' },
		{ name: 'wafw00f', version: '2.4.2', url: 'https://example.test/wafw00f' }
	],
	documentation_url: 'https://rengine.wiki',
	issue_url: 'https://github.com/yogeshojha/rengine/issues/new'
};

describe('aboutDetails', () => {
	it('lists the instance, then one tool per line', () => {
		expect(aboutDetails(about)).toBe(
			[
				'- reNgine: 3.0.0',
				'- Mode: Bug bounty',
				'- Architecture: x86_64',
				'- PostgreSQL: 16.11',
				'- Redis: Not available',
				'- Check library: 12,864 checks, synced 2026-10-04 12:38 UTC',
				'- Tools:',
				'  - dnsx v1.3.1',
				'  - wafw00f 2.4.2'
			].join('\n')
		);
	});

	it('marks a library never synced as not available', () => {
		expect(aboutDetails({ ...about, check_library: null })).toContain(
			'- Check library: Not available'
		);
	});
});

describe('checkCount', () => {
	it('prefers a stated library version over the count', () => {
		expect(checkCount({ version: 'v10.3.0', checks: 12864, synced_at: null })).toBe('v10.3.0');
		expect(checkCount({ version: null, checks: null, synced_at: null })).toBeNull();
	});
});
