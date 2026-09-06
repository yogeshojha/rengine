export type TokenKind =
	| 'field'
	| 'operator'
	| 'value'
	| 'term'
	| 'connector'
	| 'paren'
	| 'space'
	| 'invalid';

export interface QueryToken {
	kind: TokenKind;
	start: number;
	end: number;
	text: string;
}

export interface QueryProblem {
	start: number;
	end: number;
	message: string;
	level: 'error' | 'warning';
}

export interface LexResult {
	tokens: QueryToken[];
	problems: QueryProblem[];
	incomplete: boolean;
}

export type CaretContext =
	| { kind: 'field'; prefix: string; start: number; end: number }
	| { kind: 'operator'; field: string; prefix: string; start: number; end: number }
	| {
			kind: 'value';
			field: string;
			sub: string | null;
			prefix: string;
			start: number;
			end: number;
	  };

const OPERATORS = ['!=', '>=', '<=', '!~', ':', '=', '>', '<', '~'];
const CONNECTORS = new Set(['and', 'or', 'not', '&&', '||']);
const DYNAMIC_PARENT = 'header';
const FIELDISH = /^[a-z][a-z0-9_]*(\.[a-z0-9_-]+)*$/i;

export type FieldLookup = (name: string) => boolean;

function resolve(name: string, known: FieldLookup): { field: string; sub: string | null } | null {
	const key = name.toLowerCase();
	if (known(key)) return { field: key, sub: null };
	const dot = key.indexOf('.');
	if (dot > 0 && key.slice(0, dot) === DYNAMIC_PARENT && known(DYNAMIC_PARENT)) {
		return { field: DYNAMIC_PARENT, sub: key.slice(dot + 1) };
	}
	return null;
}

function readChunk(source: string, from: number): { end: number; unterminated: string | null } {
	let i = from;
	let quoted = false;
	let depth = 0;
	while (i < source.length) {
		const c = source[i];
		if (quoted) {
			if (c === '\\' && i + 1 < source.length) {
				i += 2;
				continue;
			}
			if (c === '"') quoted = false;
			i += 1;
			continue;
		}
		if (c === '"') {
			quoted = true;
			i += 1;
			continue;
		}
		if (c === '[') depth += 1;
		else if (c === ']') depth = Math.max(0, depth - 1);
		else if (depth === 0 && (/\s/.test(c) || c === '(' || c === ')')) break;
		i += 1;
	}
	return { end: i, unterminated: quoted ? 'quote' : depth ? 'bracket' : null };
}

function splitOperator(text: string, known: FieldLookup): [string, string, string] | null {
	for (let i = 1; i < text.length; i += 1) {
		for (const op of OPERATORS) {
			if (!text.startsWith(op, i)) continue;
			if (resolve(text.slice(0, i), known) === null) continue;
			return [text.slice(0, i), op, text.slice(i + op.length)];
		}
	}
	return null;
}

export function lex(source: string, known: FieldLookup): LexResult {
	const tokens: QueryToken[] = [];
	const problems: QueryProblem[] = [];
	const parens: number[] = [];
	let i = 0;

	const push = (kind: TokenKind, start: number, end: number) => {
		if (end > start) tokens.push({ kind, start, end, text: source.slice(start, end) });
	};

	while (i < source.length) {
		const c = source[i];
		if (/\s/.test(c)) {
			const start = i;
			while (i < source.length && /\s/.test(source[i])) i += 1;
			push('space', start, i);
			continue;
		}
		if (c === '(' || c === ')') {
			if (c === '(') parens.push(i);
			else if (parens.length === 0) {
				problems.push({ start: i, end: i + 1, message: 'Unmatched )', level: 'error' });
			} else parens.pop();
			push('paren', i, i + 1);
			i += 1;
			continue;
		}
		const { end, unterminated } = readChunk(source, i);
		const text = source.slice(i, end);
		if (unterminated) {
			problems.push({
				start: i,
				end,
				message:
					unterminated === 'quote' ? 'This quote is never closed' : 'This list is never closed',
				level: 'error'
			});
			push('invalid', i, end);
			i = end;
			continue;
		}
		const lowered = text.toLowerCase();
		if (CONNECTORS.has(lowered)) {
			push('connector', i, end);
			i = end;
			continue;
		}
		if (text.length > 1 && (text[0] === '-' || text[0] === '!') && !/^!(=|~)/.test(text)) {
			push('connector', i, i + 1);
			i += 1;
			continue;
		}
		const split = splitOperator(text, known);
		if (split) {
			const [name, op, rest] = split;
			push('field', i, i + name.length);
			push('operator', i + name.length, i + name.length + op.length);
			push('value', i + name.length + op.length, end);
			if (!rest) {
				const next = nextChunk(source, end);
				if (next) {
					push('space', end, next.start);
					push('value', next.start, next.end);
					i = next.end;
					continue;
				}
			}
			i = end;
			continue;
		}
		if (resolve(text, known)) {
			const after = peekOperator(source, end);
			if (after) {
				push('field', i, end);
				push('space', end, after.opStart);
				push('operator', after.opStart, after.opEnd);
				const next = nextChunk(source, after.opEnd);
				if (next) {
					push('space', after.opEnd, next.start);
					push('value', next.start, next.end);
					i = next.end;
				} else i = after.opEnd;
				continue;
			}
		}
		if (FIELDISH.test(text.split(':')[0]) && text.includes(':') && !text.includes('//')) {
			problems.push({
				start: i,
				end: i + text.indexOf(':'),
				message: `"${text.slice(0, text.indexOf(':'))}" is not a field, searched as text`,
				level: 'warning'
			});
		}
		push('term', i, end);
		i = end;
	}
	for (const open of parens) {
		problems.push({
			start: open,
			end: open + 1,
			message: 'This group is never closed',
			level: 'error'
		});
	}
	const tail = tokens.filter((t) => t.kind !== 'space').at(-1);
	const incomplete = tail?.kind === 'operator' || tail?.kind === 'connector';
	return { tokens, problems, incomplete };
}

function nextChunk(source: string, from: number): { start: number; end: number } | null {
	let i = from;
	while (i < source.length && /\s/.test(source[i])) i += 1;
	if (i >= source.length || source[i] === '(' || source[i] === ')') return null;
	const { end } = readChunk(source, i);
	return end > i ? { start: i, end } : null;
}

function peekOperator(source: string, from: number): { opStart: number; opEnd: number } | null {
	let i = from;
	while (i < source.length && /\s/.test(source[i])) i += 1;
	for (const op of OPERATORS) {
		if (source.startsWith(op, i)) return { opStart: i, opEnd: i + op.length };
	}
	return null;
}

export function caretContext(
	source: string,
	caret: number,
	known: FieldLookup
): CaretContext | null {
	if (caret < source.length && !/[\s()]/.test(source[caret])) return null;
	let start = caret;
	while (start > 0 && !/[\s()]/.test(source[start - 1])) start -= 1;
	const head = source.slice(start, caret);
	if (!head) return { kind: 'field', prefix: '', start: caret, end: caret };
	if (CONNECTORS.has(head.toLowerCase())) {
		return { kind: 'field', prefix: head, start, end: caret };
	}
	const split = splitOperator(head, known);
	if (split) {
		const [name, , rest] = split;
		const target = resolve(name, known);
		if (!target) return { kind: 'field', prefix: head, start, end: caret };
		return {
			kind: 'value',
			field: target.field,
			sub: target.sub,
			prefix: unquote(rest),
			start: start + name.length + split[1].length,
			end: caret
		};
	}
	const spaced = spacedOperator(source, start, caret, known);
	if (spaced) return spaced;
	return { kind: 'field', prefix: head, start, end: caret };
}

function spacedOperator(
	source: string,
	start: number,
	caret: number,
	known: FieldLookup
): CaretContext | null {
	const before = source.slice(0, start).trimEnd();
	const opMatch = /(!=|>=|<=|!~|[:=><~])$/.exec(before);
	if (!opMatch) return null;
	const head = before.slice(0, before.length - opMatch[0].length).trimEnd();
	const nameStart = Math.max(head.lastIndexOf(' '), head.lastIndexOf('(')) + 1;
	const target = resolve(head.slice(nameStart), known);
	if (!target) return null;
	return {
		kind: 'value',
		field: target.field,
		sub: target.sub,
		prefix: unquote(source.slice(start, caret)),
		start,
		end: caret
	};
}

export function unquote(value: string): string {
	if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) return value.slice(1, -1);
	return value.startsWith('"') ? value.slice(1) : value;
}

export function quoteValue(value: string): string {
	return /[\s()"[\]:=><~]/.test(value) ? `"${value.replace(/"/g, '\\"')}"` : value;
}

export function replaceRange(source: string, start: number, end: number, insert: string): string {
	return source.slice(0, start) + insert + source.slice(end);
}
