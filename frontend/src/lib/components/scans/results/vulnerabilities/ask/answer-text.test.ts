import { describe, expect, it } from 'vitest';
import { cited, parseAnswer, spans } from './answer-text';

describe('spans', () => {
	it('splits citations, bold and code out of prose', () => {
		expect(
			spans('Both came back in the body [[1]], the pair **the matcher** needs `word-1`.')
		).toEqual([
			{ kind: 'text', text: 'Both came back in the body ' },
			{ kind: 'cite', n: 1 },
			{ kind: 'text', text: ', the pair ' },
			{ kind: 'bold', text: 'the matcher' },
			{ kind: 'text', text: ' needs ' },
			{ kind: 'code', text: 'word-1' },
			{ kind: 'text', text: '.' }
		]);
	});

	it('keeps adjacent citations apart', () => {
		expect(spans('seen [[1]][[2]]')).toEqual([
			{ kind: 'text', text: 'seen ' },
			{ kind: 'cite', n: 1 },
			{ kind: 'cite', n: 2 }
		]);
	});
});

describe('parseAnswer', () => {
	it('joins wrapped lines into one paragraph and splits on blank lines', () => {
		const blocks = parseAnswer('First line\nsecond line.\n\nNew paragraph.');
		expect(blocks).toHaveLength(2);
		expect(blocks[0].kind).toBe('p');
		expect(blocks[0].spans).toEqual([{ kind: 'text', text: 'First line second line.' }]);
	});

	it('reads numbered and bulleted lines as items', () => {
		const blocks = parseAnswer('1. Send the request [[1]]\n2) Read the body\n- note');
		expect(blocks.map((b) => [b.kind, b.n])).toEqual([
			['item', 1],
			['item', 2],
			['item', null]
		]);
		expect(cited(blocks)).toEqual([1]);
	});
});
