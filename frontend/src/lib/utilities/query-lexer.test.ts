import { describe, expect, it } from 'vitest';
import { lex, quoteValue } from './query-lexer';

const known = () => true;

function values(source: string): string[] {
	return lex(source, known)
		.tokens.filter((t) => t.kind === 'value')
		.map((t) => t.text);
}

describe('quoteValue', () => {
	it('leaves a plain value bare', () => {
		expect(quoteValue('nginx')).toBe('nginx');
	});

	it('keeps a value ending in a backslash inside its own quotes', () => {
		const query = `title:${quoteValue('C:\\')} status:200`;
		expect(values(query)).toEqual([quoteValue('C:\\'), '200']);
	});

	it('does not let a scanned backslash-quote close the quote early', () => {
		const query = `title:${quoteValue('a\\" or b')}`;
		expect(values(query)).toEqual([quoteValue('a\\" or b')]);
		expect(lex(query, known).tokens.filter((t) => t.kind === 'connector')).toEqual([]);
	});
});
