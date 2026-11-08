import { HighlightStyle } from '@codemirror/language';
import {
	TAG_KINDS,
	KIND_VARS,
	KIND_WEIGHTS,
	type CodeLine,
	type TokenKind
} from './code-highlight';

export const codeHighlightStyle = HighlightStyle.define(
	TAG_KINDS.map(({ tag, kind }) => ({
		tag,
		color: KIND_VARS[kind],
		...(KIND_WEIGHTS[kind] ? { fontWeight: KIND_WEIGHTS[kind] } : {}),
		...(kind === 'comment' ? { fontStyle: 'italic' } : {})
	}))
);

type TokenStyle = Record<string, string>;

/** The style of each token kind, as code-block.svelte renders it. */
export const TOKEN_STYLES = Object.fromEntries(
	(Object.keys(KIND_VARS) as TokenKind[])
		.filter((kind) => kind !== 'text')
		.map((kind): [TokenKind, TokenStyle] => [
			kind,
			{
				color: KIND_VARS[kind],
				...(KIND_WEIGHTS[kind] ? { fontWeight: KIND_WEIGHTS[kind] } : {}),
				...(kind === 'comment' ? { fontStyle: 'italic' } : {}),
				...(kind === 'link'
					? {
							textDecoration: 'underline',
							textDecorationColor: 'color-mix(in oklch, var(--code-link) 40%, transparent)',
							textUnderlineOffset: '2px'
						}
					: {})
			}
		])
) as Partial<Record<TokenKind, TokenStyle>>;

export interface TokenRange {
	from: number;
	to: number;
	kind: TokenKind;
}

/** Document offsets of each coloured token, or null when the tokens do not spell the text. */
export function tokenRanges(lines: CodeLine[], length: number): TokenRange[] | null {
	const out: TokenRange[] = [];
	let at = 0;
	lines.forEach((line, index) => {
		if (index) at += 1;
		for (const token of line) {
			const to = at + token.text.length;
			if (token.kind !== 'text' && to > at) out.push({ from: at, to, kind: token.kind });
			at = to;
		}
	});
	return at === length ? out : null;
}
