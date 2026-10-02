import { describe, expect, it } from 'vitest';
import { appendToken, appendTokens } from './scan-insights';

describe('appendToken', () => {
	it('adds a token to a plain query', () => {
		expect(appendToken('status:200', 'tech:nginx')).toBe('status:200 tech:nginx');
	});

	it('keeps a query that already holds the token', () => {
		expect(appendToken('status:200 tech:nginx', 'tech:nginx')).toBe('status:200 tech:nginx');
	});

	it('groups a top-level or before narrowing it', () => {
		expect(appendToken('a or b', 'severity:high')).toBe('(a or b) severity:high');
		expect(appendToken('a || b', 'severity:high')).toBe('(a || b) severity:high');
		expect(appendToken('a OR b', 'severity:high')).toBe('(a OR b) severity:high');
	});

	it('leaves an or inside a group alone', () => {
		expect(appendToken('(a or b) c', 'd')).toBe('(a or b) c d');
	});

	it('ignores an or inside quotes', () => {
		expect(appendToken('title:"this or that"', 'd')).toBe('title:"this or that" d');
	});

	it('narrows every branch when several tokens are added', () => {
		expect(appendTokens('a or b', ['c', 'd'])).toBe('(a or b) c d');
	});
});
