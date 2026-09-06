import { HighlightStyle } from '@codemirror/language';
import { TAG_KINDS, KIND_VARS, KIND_WEIGHTS } from './code-highlight';

export const codeHighlightStyle = HighlightStyle.define(
	TAG_KINDS.map(({ tag, kind }) => ({
		tag,
		color: KIND_VARS[kind],
		...(KIND_WEIGHTS[kind] ? { fontWeight: KIND_WEIGHTS[kind] } : {}),
		...(kind === 'comment' ? { fontStyle: 'italic' } : {})
	}))
);
