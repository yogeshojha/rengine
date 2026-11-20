import { describe, expect, it } from 'vitest';
import { scopeClause } from '$lib/components/dashboard/scope-links';
import { lex, quoteListItem, quoteValue, quoted, unquote } from './query-lexer';

const known = () => true;

function values(source: string): string[] {
	return lex(source, known)
		.tokens.filter((t) => t.kind === 'value')
		.map((t) => t.text);
}

const ROUND_TRIP = [
	'a\\b',
	'a\\"b',
	'a\\',
	'C:\\',
	'C:\\Windows\\System32',
	'\\\\srv\\share',
	'say "hi"',
	'a\\" or b',
	' x ',
	'line\none'
];

// written by shared/services/asset_query/tokens.py:token for the same values
const BACKEND = new Map([
	['a\\b', 'a\\b'],
	['a\\"b', '"a\\\\\\"b"'],
	['a\\', 'a\\'],
	['C:\\', '"C:\\\\"'],
	['C:\\Windows\\System32', '"C:\\\\Windows\\\\System32"'],
	['say "hi"', '"say \\"hi\\""'],
	['', '""']
]);

describe('quoteValue', () => {
	it('leaves a plain value bare', () => {
		expect(quoteValue('nginx')).toBe('nginx');
		expect(quoteValue('a,b')).toBe('a,b');
	});

	it('writes what the backend writes', () => {
		for (const [value, written] of BACKEND) expect(quoteValue(value)).toBe(written);
	});

	it('reads back every value as one token', () => {
		for (const value of ROUND_TRIP) {
			const query = `title:${quoteValue(value)} status:200`;
			const read = values(query);
			expect(read).toEqual([quoteValue(value), '200']);
			expect(unquote(read[0])).toBe(value);
		}
	});

	it('does not let a scanned backslash-quote close the quote early', () => {
		const query = `title:${quoteValue('a\\" or b')}`;
		expect(lex(query, known).tokens.filter((t) => t.kind === 'connector')).toEqual([]);
		expect(lex(query, known).problems).toEqual([]);
	});
});

describe('quoted', () => {
	it('always quotes and escapes', () => {
		expect(quoted('nginx')).toBe('"nginx"');
		expect(quoted('a\\"b')).toBe('"a\\\\\\"b"');
		for (const value of ROUND_TRIP) expect(unquote(quoted(value))).toBe(value);
	});
});

describe('quoteListItem', () => {
	it('quotes a comma the list would split on', () => {
		expect(quoteListItem('a,b')).toBe('"a,b"');
		expect(quoteListItem('a.com')).toBe('a.com');
	});

	it('writes a control character raw, never as a JSON escape', () => {
		expect(quoteListItem('a\tb.example')).toBe('"a\tb.example"');
		expect(unquote(quoteListItem('a\tb.example'))).toBe('a\tb.example');
	});

	it('keeps a list of awkward values intact', () => {
		const query = `title:[${ROUND_TRIP.map(quoteListItem).join(',')}] status:200`;
		expect(values(query)).toHaveLength(2);
		expect(lex(query, known).problems).toEqual([]);
	});
});

describe('scopeClause', () => {
	it('quotes targets through the lexer helpers', () => {
		expect(scopeClause(['a\\" b'])).toBe(`target=${quoteValue('a\\" b')}`);
		expect(scopeClause(['a,b', 'c'])).toBe('target=["a,b",c]');
		expect(lex(scopeClause(['x\\"', 'y']), known).problems).toEqual([]);
	});
});
