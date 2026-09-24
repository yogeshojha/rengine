import { describe, expect, it } from 'vitest';
import { scopeFromParams, scopeToParams } from './dashboard-scope';
import { sameTargetScope, scopeQuery } from './surface-scope';
import { scopeClause, withClause } from '$lib/components/dashboard/scope-links';

describe('dashboard scope', () => {
	it('round-trips through the URL', () => {
		const scope = { targetIds: ['a', 'b'], organizationId: 'o', tagId: 't' };
		const back = scopeFromParams(scopeToParams(new URLSearchParams('x=1'), scope));
		expect(sameTargetScope(back, scope)).toBe(true);
	});

	it('reads an empty URL as no scope', () => {
		expect(scopeFromParams(new URLSearchParams())).toEqual({
			targetIds: undefined,
			organizationId: undefined,
			tagId: undefined
		});
	});

	it('sends each target as its own parameter', () => {
		expect(scopeQuery({ projectId: 'p', targetIds: ['a', 'b'] })).toBe(
			'project_id=p&target_id=a&target_id=b'
		);
	});

	it('scopes a link query by exact target', () => {
		const clause = scopeClause(['a.com', 'b.com']);
		expect(clause).toBe('target=[a.com,b.com]');
		expect(scopeClause(['a.com'])).toBe('target=a.com');
		expect(withClause(clause, 'is:live or is:new')).toBe(
			'target=[a.com,b.com] and (is:live or is:new)'
		);
		expect(withClause(clause, '')).toBe('target=[a.com,b.com]');
		expect(withClause('', 'is:live')).toBe('is:live');
	});
});
