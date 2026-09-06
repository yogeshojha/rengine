import { parser as yamlParser } from '@lezer/yaml';
import { highlightCode, tagHighlighter, tags as t, type Tag } from '@lezer/highlight';

export type CodeLang = 'yaml' | 'json' | 'http' | 'shell' | 'text';

export type TokenKind =
	| 'text'
	| 'comment'
	| 'key'
	| 'string'
	| 'scalar'
	| 'number'
	| 'atom'
	| 'keyword'
	| 'punct'
	| 'meta'
	| 'link'
	| 'invalid'
	| 'ok'
	| 'redir'
	| 'warn'
	| 'err';

export interface CodeToken {
	text: string;
	kind: TokenKind;
	mark?: boolean;
}

export type CodeLine = CodeToken[];

export const LANG_LABELS: Record<CodeLang, string> = {
	yaml: 'YAML',
	json: 'JSON',
	http: 'HTTP',
	shell: 'Shell',
	text: 'Text'
};

export const KIND_VARS: Record<TokenKind, string> = {
	text: 'var(--code-fg)',
	comment: 'var(--code-comment)',
	key: 'var(--code-key)',
	string: 'var(--code-string)',
	scalar: 'var(--code-string)',
	number: 'var(--code-number)',
	atom: 'var(--code-atom)',
	keyword: 'var(--code-keyword)',
	punct: 'var(--code-punct)',
	meta: 'var(--code-meta)',
	link: 'var(--code-link)',
	invalid: 'var(--destructive)',
	ok: 'var(--success)',
	redir: 'var(--info)',
	warn: 'var(--warning)',
	err: 'var(--destructive)'
};

export const KIND_WEIGHTS: Partial<Record<TokenKind, string>> = {
	key: '600',
	keyword: '500',
	ok: '600',
	redir: '600',
	warn: '600',
	err: '600'
};

export const TAG_KINDS: { tag: Tag | readonly Tag[]; kind: TokenKind }[] = [
	{ tag: [t.comment, t.lineComment, t.blockComment], kind: 'comment' },
	{ tag: [t.propertyName, t.definition(t.propertyName), t.labelName], kind: 'key' },
	{ tag: t.content, kind: 'scalar' },
	{ tag: [t.string, t.special(t.string), t.attributeValue], kind: 'string' },
	{ tag: [t.number, t.integer, t.float], kind: 'number' },
	{ tag: [t.bool, t.null, t.atom, t.keyword], kind: 'atom' },
	{
		tag: [t.punctuation, t.separator, t.bracket, t.brace, t.squareBracket, t.paren],
		kind: 'punct'
	},
	{ tag: [t.meta, t.typeName], kind: 'meta' },
	{ tag: t.invalid, kind: 'invalid' }
];

const MAX_HIGHLIGHT_BYTES = 400_000;

const YAML_ATOM = /^(true|false|null|~|yes|no|on|off|True|False|Null|TRUE|FALSE|NULL)$/;
const YAML_NUMBER = /^[+-]?(?:\d[\d_]*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const URL_RE = /^(?:https?|ftp|wss?):\/\/\S+$/i;

const yamlHighlighter = tagHighlighter(
	TAG_KINDS.map((entry) => ({ tag: entry.tag, class: entry.kind }))
);

function push(line: CodeLine, text: string, kind: TokenKind) {
	if (!text) return;
	const last = line[line.length - 1];
	if (last && last.kind === kind) last.text += text;
	else line.push({ text, kind });
}

function emit(lines: CodeLine[], raw: string, kind: TokenKind) {
	const parts = raw.split('\n');
	for (let index = 0; index < parts.length; index++) {
		if (index) lines.push([]);
		push(lines[lines.length - 1], parts[index], kind);
	}
}

function* scan(code: string, pattern: RegExp): Generator<[string, number]> {
	let cursor = 0;
	while (cursor < code.length) {
		pattern.lastIndex = cursor;
		const match = pattern.exec(code);
		if (!match || !match[0].length) {
			yield [code[cursor], cursor];
			cursor += 1;
			continue;
		}
		yield [match[0], cursor];
		cursor = pattern.lastIndex;
	}
}

function plainLines(code: string): CodeLine[] {
	return code.split('\n').map((line) => (line ? [{ text: line, kind: 'text' as const }] : []));
}

function refineScalar(token: CodeToken): CodeToken {
	if (token.kind !== 'scalar') return token;
	const value = token.text.trim();
	if (YAML_ATOM.test(value)) return { ...token, kind: 'atom' };
	if (YAML_NUMBER.test(value)) return { ...token, kind: 'number' };
	if (URL_RE.test(value)) return { ...token, kind: 'link' };
	return { ...token, kind: 'string' };
}

function highlightYaml(code: string): CodeLine[] {
	const lines: CodeLine[] = [[]];
	highlightCode(
		code,
		yamlParser.parse(code),
		yamlHighlighter,
		(text, classes) => push(lines[lines.length - 1], text, (classes || 'text') as TokenKind),
		() => lines.push([])
	);
	return lines.map((line) => line.map(refineScalar));
}

const JSON_TOKEN =
	/"(?:[^"\\]|\\.)*"?|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\btrue\b|\bfalse\b|\bnull\b|[{}[\],:]|\s+|[^\s{}[\],:"]+/y;

function tokenizeJsonInto(code: string, lines: CodeLine[]) {
	for (const [raw, at] of scan(code, JSON_TOKEN)) {
		let kind: TokenKind;
		if (raw[0] === '"') {
			kind = /^\s*:/.test(code.slice(at + raw.length)) ? 'key' : 'string';
			if (kind === 'string' && URL_RE.test(raw.slice(1, -1))) kind = 'link';
		} else if (/^-?[\d.]/.test(raw)) kind = 'number';
		else if (raw === 'true' || raw === 'false' || raw === 'null') kind = 'atom';
		else if (/^[{}[\],:]$/.test(raw)) kind = 'punct';
		else if (!raw.trim()) kind = 'text';
		else kind = 'invalid';
		emit(lines, raw, kind);
	}
}

function highlightJson(code: string): CodeLine[] {
	const lines: CodeLine[] = [[]];
	tokenizeJsonInto(code, lines);
	return lines;
}

const REQUEST_LINE = /^([A-Z][A-Z-]{1,14})([ \t]+)(\S+)([ \t]+HTTP\/[\d.]+)?([ \t]*)$/;
const STATUS_LINE = /^(HTTP\/[\d.]+)([ \t]+)(\d{3})(.*)$/;
const HEADER_LINE = /^([A-Za-z0-9!#$%&'*+.^_`|~-]+)(:)([ \t]*)(.*)$/;

function statusKind(status: number): TokenKind {
	if (status >= 500) return 'err';
	if (status >= 400) return 'warn';
	if (status >= 300) return 'redir';
	if (status >= 200) return 'ok';
	return 'meta';
}

function httpHead(line: string): CodeLine | null {
	const request = REQUEST_LINE.exec(line);
	if (request) {
		const out: CodeLine = [];
		push(out, request[1], 'keyword');
		push(out, request[2], 'text');
		push(out, request[3], URL_RE.test(request[3]) ? 'link' : 'string');
		push(out, request[4] ?? '', 'meta');
		push(out, request[5], 'text');
		return out;
	}
	const status = STATUS_LINE.exec(line);
	if (status) {
		const out: CodeLine = [];
		push(out, status[1], 'meta');
		push(out, status[2], 'text');
		push(out, status[3], statusKind(Number(status[3])));
		push(out, status[4], 'text');
		return out;
	}
	return null;
}

function headerLine(raw: string): CodeLine {
	const header = HEADER_LINE.exec(raw);
	if (!header) return raw ? [{ text: raw, kind: 'text' }] : [];
	const out: CodeLine = [];
	push(out, header[1], 'key');
	push(out, header[2], 'punct');
	push(out, header[3], 'text');
	push(out, header[4], URL_RE.test(header[4].trimEnd()) ? 'link' : 'text');
	return out;
}

function highlightHttp(code: string): CodeLine[] {
	const source = code.split('\n');
	const lines: CodeLine[] = [];
	let mode: 'head' | 'headers' | 'body' = 'head';

	for (let index = 0; index < source.length; index++) {
		const full = source[index];
		const raw = full.endsWith('\r') ? full.slice(0, -1) : full;
		const cr = full.length - raw.length;
		const put = (line: CodeLine) => {
			if (cr) push(line, '\r', 'text');
			lines.push(line);
		};

		if (mode !== 'headers') {
			const head = httpHead(raw);
			if (head) {
				put(head);
				mode = 'headers';
				continue;
			}
			if (mode === 'head' && HEADER_LINE.test(raw)) mode = 'headers';
		}

		if (mode === 'headers') {
			if (raw.trim()) {
				put(headerLine(raw));
				continue;
			}
			put(raw ? [{ text: raw, kind: 'text' }] : []);
			const body = source.slice(index + 1);
			const first = body.find((line) => line.trim());
			if (first && /^[{[]/.test(first.trim())) {
				const nested: CodeLine[] = [[]];
				tokenizeJsonInto(body.join('\n'), nested);
				lines.push(...nested);
				return lines;
			}
			mode = 'body';
			continue;
		}

		put(raw ? [{ text: raw, kind: 'text' }] : []);
	}
	return lines;
}

const SHELL_TOKEN =
	/'(?:[^'\\]|\\.)*'?|"(?:[^"\\]|\\.)*"?|`(?:[^`\\]|\\.)*`?|\$\{[^}]*\}?|\$[A-Za-z_]\w*|#[^\n]*|\\\n?|\|\||&&|[|;&<>]|[ \t]+|\n|[^\s'"`$|;&<>\\#]+/y;
const SHELL_FLAG = /^--?[A-Za-z0-9][\w-]*$/;

function highlightShell(code: string): CodeLine[] {
	const lines: CodeLine[] = [[]];
	let expectCommand = true;

	for (const [raw] of scan(code, SHELL_TOKEN)) {
		let kind: TokenKind = 'text';

		if (raw[0] === '#') kind = 'comment';
		else if (raw[0] === "'" || raw[0] === '"' || raw[0] === '`') kind = 'string';
		else if (raw[0] === '$') kind = 'atom';
		else if (raw[0] === '\\' || /^(\|\||&&|[|;&<>])$/.test(raw)) {
			kind = 'punct';
			expectCommand = raw !== '\\';
		} else if (!raw.trim()) {
			if (raw.includes('\n')) expectCommand = true;
		} else if (URL_RE.test(raw)) kind = 'link';
		else if (SHELL_FLAG.test(raw)) kind = 'meta';
		else if (expectCommand) {
			kind = 'keyword';
			expectCommand = false;
		} else if (/^-?\d+(\.\d+)?$/.test(raw)) kind = 'number';

		emit(lines, raw, kind);
	}
	return lines;
}

export function highlight(code: string, lang: CodeLang = 'text'): CodeLine[] {
	if (!code) return [];
	if (code.length > MAX_HIGHLIGHT_BYTES) return plainLines(code);
	try {
		switch (lang) {
			case 'yaml':
				return highlightYaml(code);
			case 'json':
				return highlightJson(code);
			case 'http':
				return highlightHttp(code);
			case 'shell':
				return highlightShell(code);
			default:
				return plainLines(code);
		}
	} catch {
		return plainLines(code);
	}
}

export function applyMarks(lines: CodeLine[], terms: string[]): CodeLine[] {
	const needles = [...new Set(terms.map((term) => term.toLowerCase()))].filter(
		(term) => term.length > 1
	);
	if (!needles.length) return lines;

	return lines.map((line) => {
		const out: CodeLine = [];
		for (const token of line) {
			const lower = token.text.toLowerCase();
			let cursor = 0;
			while (cursor < token.text.length) {
				let at = -1;
				let length = 0;
				for (const needle of needles) {
					const found = lower.indexOf(needle, cursor);
					if (found < 0) continue;
					if (at < 0 || found < at || (found === at && needle.length > length)) {
						at = found;
						length = needle.length;
					}
				}
				if (at < 0) {
					out.push({ text: token.text.slice(cursor), kind: token.kind });
					break;
				}
				if (at > cursor) out.push({ text: token.text.slice(cursor, at), kind: token.kind });
				out.push({ text: token.text.slice(at, at + length), kind: token.kind, mark: true });
				cursor = at + length;
			}
		}
		return out;
	});
}

export function guessLang(code: string, fallback: CodeLang = 'text'): CodeLang {
	const head = code.slice(0, 400).trimStart();
	if (!head) return fallback;
	const first = head.split('\n', 1)[0];
	if (REQUEST_LINE.test(first) || STATUS_LINE.test(first)) return 'http';
	if (head[0] === '{' || head[0] === '[') return 'json';
	if (/^(curl|docker|npm|npx|python|sh|bash|git|nuclei|httpx|naabu|subfinder)\b/.test(head))
		return 'shell';
	return fallback;
}
