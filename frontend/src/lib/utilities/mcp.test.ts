import { describe, expect, it } from 'vitest';
import { inAppHref } from './mcp';

describe('inAppHref', () => {
	it('keeps the path, query and fragment of a pivot', () => {
		expect(inAppHref('https://rengine.example/scans/1?tab=dns#a')).toBe('/scans/1?tab=dns#a');
		expect(inAppHref('/targets/1')).toBe('/targets/1');
	});

	it('drops a pivot that is not an in-app path', () => {
		expect(inAppHref('javascript:alert(1)')).toBeUndefined();
		expect(inAppHref('https://rengine.example//evil.example/x')).toBeUndefined();
		expect(inAppHref('//evil.example')).toBeUndefined();
		expect(inAppHref('scans/1')).toBeUndefined();
	});
});
