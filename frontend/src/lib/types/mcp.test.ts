import { describe, expect, it } from 'vitest';
import { regrant } from './mcp';

const ALL = new Set(['read', 'plan', 'write', 'launch']);

describe('regrant', () => {
	it('leaves a partial grant alone when the rung did not move', () => {
		expect(regrant(3, ['read', 'plan', 'launch'], ALL)).toBeUndefined();
	});

	it('rebuilds the grant when the rung moved', () => {
		expect(regrant(1, ['read', 'plan', 'launch'], ALL)).toEqual(['read', 'plan']);
	});

	it('stays inside the ceiling on a raise', () => {
		expect(regrant(3, ['read'], new Set(['read', 'plan', 'launch']))).toEqual([
			'read',
			'plan',
			'launch'
		]);
	});
});
