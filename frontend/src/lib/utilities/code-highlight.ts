import { parser as yamlParser } from '@lezer/yaml';
import { highlightCode, tagHighlighter, tags as t, type Tag } from '@lezer/highlight';

export type CodeLang = 'yaml' | 'json' | 'http' | 'shell' | 'html' | 'xml' | 'css' | 'js' | 'text';

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
	| 'tag'
	| 'attr'
	| 'fn'
	| 'op'
	| 'ok'
	| 'redir'
	| 'warn'
	| 'err';

export interface CodeToken {
	text: string;
	kind: TokenKind;
	mark?: boolean;
	hit?: number;
}

export type CodeLine = CodeToken[];

export const LANG_LABELS: Record<CodeLang, string> = {
	yaml: 'YAML',
	json: 'JSON',
	http: 'HTTP',
	shell: 'Shell',
	html: 'HTML',
	xml: 'XML',
	css: 'CSS',
	js: 'JavaScript',
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
	tag: 'var(--code-tag)',
	attr: 'var(--code-attr)',
	fn: 'var(--code-fn)',
	op: 'var(--code-op)',
	ok: 'var(--success)',
	redir: 'var(--info)',
	warn: 'var(--warning)',
	err: 'var(--destructive)'
};

export const KIND_WEIGHTS: Partial<Record<TokenKind, string>> = {
	key: '600',
	tag: '500',
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

const CSS_TOKEN =
	/\/\*[\s\S]*?(?:\*\/|$)|"(?:[^"\\]|\\.)*"?|'(?:[^'\\]|\\.)*'?|url\([^)]*\)?|@[\w-]+|#[0-9a-fA-F]{3,8}\b|[-+]?(?:\d*\.\d+|\d+)(?:[a-zA-Z%]+)?|[\w-]+|\s+|[\s\S]/y;

function tokenizeCssInto(code: string, lines: CodeLine[]) {
	let inBlock = false;
	let afterColon = false;
	for (const [raw, at] of scan(code, CSS_TOKEN)) {
		let kind: TokenKind = 'text';
		if (raw.startsWith('/*')) kind = 'comment';
		else if (raw[0] === '"' || raw[0] === "'") kind = 'string';
		else if (raw.startsWith('url(')) kind = 'link';
		else if (raw[0] === '@') kind = 'keyword';
		else if (raw[0] === '#') kind = 'number';
		else if (/^[-+]?[\d.]/.test(raw)) kind = 'number';
		else if (raw === '{') {
			kind = 'punct';
			inBlock = true;
			afterColon = false;
		} else if (raw === '}') {
			kind = 'punct';
			inBlock = false;
			afterColon = false;
		} else if (raw === ';') {
			kind = 'punct';
			afterColon = false;
		} else if (raw === ':') {
			kind = 'punct';
			if (inBlock) afterColon = true;
		} else if (!raw.trim()) kind = 'text';
		else if (/^[\w-]+$/.test(raw)) {
			if (!inBlock) kind = 'fn';
			else if (afterColon) kind = 'atom';
			else if (/^\s*:/.test(code.slice(at + raw.length))) kind = 'key';
		} else kind = 'punct';
		emit(lines, raw, kind);
	}
}

const JS_KEYWORDS = new Set(
	(
		'var let const function return if else for while do switch case break continue new delete typeof ' +
		'instanceof in of class extends super this async await yield try catch finally throw import export ' +
		'from default void with static get set'
	).split(' ')
);
const JS_ATOMS = new Set(['true', 'false', 'null', 'undefined', 'NaN', 'Infinity']);
const JS_TOKEN =
	/\/\*[\s\S]*?(?:\*\/|$)|\/\/[^\n]*|"(?:[^"\\\n]|\\.)*"?|'(?:[^'\\\n]|\\.)*'?|`(?:[^`\\]|\\.)*`?|[-+]?(?:0[xXbBoO][\da-fA-F_]+|\d[\d_]*\.?\d*(?:[eE][-+]?\d+)?|\.\d+)|[A-Za-z_$][\w$]*|=>|===|!==|[=!<>+\-*/%&|^~?:]+|\s+|[\s\S]/y;

function tokenizeJsInto(code: string, lines: CodeLine[]) {
	for (const [raw, at] of scan(code, JS_TOKEN)) {
		let kind: TokenKind = 'text';
		if (raw.startsWith('/*') || raw.startsWith('//')) kind = 'comment';
		else if (raw[0] === '"' || raw[0] === "'" || raw[0] === '`') kind = 'string';
		else if (/^[-+]?[\d.]/.test(raw)) kind = 'number';
		else if (JS_ATOMS.has(raw)) kind = 'atom';
		else if (JS_KEYWORDS.has(raw)) kind = 'keyword';
		else if (/^[A-Za-z_$]/.test(raw)) {
			kind = /^\s*\(/.test(code.slice(at + raw.length)) ? 'fn' : 'text';
		} else if (!raw.trim()) kind = 'text';
		else if (/^[{}[\]();,.]+$/.test(raw)) kind = 'punct';
		else kind = 'op';
		emit(lines, raw, kind);
	}
}

const MARKUP_OPEN = /<\/?([A-Za-z][\w:.-]*)/y;
const MARKUP_ATTR = /\s+|[^\s=/>]+|=|"(?:[^"]*)"?|'(?:[^']*)'?|\/?>|[\s\S]/y;
const VOID_TAGS = new Set([
	'area',
	'base',
	'br',
	'col',
	'embed',
	'hr',
	'img',
	'input',
	'link',
	'meta',
	'param',
	'source',
	'track',
	'wbr'
]);

function tokenizeMarkupInto(code: string, lines: CodeLine[]) {
	let i = 0;
	while (i < code.length) {
		const next = code.indexOf('<', i);
		if (next < 0) {
			emit(lines, code.slice(i), 'text');
			return;
		}
		if (next > i) emit(lines, code.slice(i, next), 'text');
		i = next;

		if (code.startsWith('<!--', i)) {
			const end = code.indexOf('-->', i + 4);
			const stop = end < 0 ? code.length : end + 3;
			emit(lines, code.slice(i, stop), 'comment');
			i = stop;
			continue;
		}
		if (code.startsWith('<!', i) || code.startsWith('<?', i)) {
			const end = code.indexOf('>', i);
			const stop = end < 0 ? code.length : end + 1;
			emit(lines, code.slice(i, stop), 'meta');
			i = stop;
			continue;
		}

		MARKUP_OPEN.lastIndex = i;
		const open = MARKUP_OPEN.exec(code);
		if (!open) {
			emit(lines, code[i], 'text');
			i += 1;
			continue;
		}
		const name = open[1].toLowerCase();
		emit(lines, open[0].startsWith('</') ? '</' : '<', 'punct');
		emit(lines, open[1], 'tag');
		i = MARKUP_OPEN.lastIndex;

		let closed = false;
		while (i < code.length && !closed) {
			MARKUP_ATTR.lastIndex = i;
			const part = MARKUP_ATTR.exec(code);
			if (!part) break;
			const raw = part[0];
			if (raw === '>' || raw === '/>') {
				emit(lines, raw, 'punct');
				closed = true;
			} else if (raw === '=') emit(lines, raw, 'punct');
			else if (raw[0] === '"' || raw[0] === "'") emit(lines, raw, 'string');
			else if (!raw.trim()) emit(lines, raw, 'text');
			else emit(lines, raw, 'attr');
			i = MARKUP_ATTR.lastIndex;
		}

		if ((name === 'script' || name === 'style') && !open[0].startsWith('</')) {
			const close = new RegExp(`</${name}\\s*>`, 'i');
			close.lastIndex = 0;
			const rest = code.slice(i);
			const found = close.exec(rest);
			const inner = found ? rest.slice(0, found.index) : rest;
			if (inner) {
				if (name === 'script') tokenizeJsInto(inner, lines);
				else tokenizeCssInto(inner, lines);
			}
			i += inner.length;
		}
	}
}

const CONTENT_TYPE = /^content-type$/i;

export function langForContentType(contentType: string | null, body = ''): CodeLang {
	const value = (contentType ?? '').toLowerCase().split(';')[0].trim();
	if (value) {
		if (value === 'text/json' || value === 'application/json' || value.endsWith('+json'))
			return 'json';
		if (value === 'text/html' || value === 'application/xhtml+xml') return 'html';
		if (/javascript|ecmascript/.test(value)) return 'js';
		if (value === 'text/css') return 'css';
		if (value === 'text/xml' || value === 'application/xml' || value.endsWith('+xml')) return 'xml';
		if (/ya?ml/.test(value)) return 'yaml';
		if (value === 'text/plain' || value === 'application/octet-stream') {
			const head = body.trimStart()[0];
			return head === '{' || head === '[' ? 'json' : 'text';
		}
		if (value.startsWith('text/')) return sniffLang(body, 'text');
		return 'text';
	}
	return sniffLang(body, 'text');
}

function sniffLang(body: string, fallback: CodeLang): CodeLang {
	const head = body.trimStart().slice(0, 200);
	if (!head) return fallback;
	if (head[0] === '{' || head[0] === '[') return 'json';
	if (/^<\?xml/i.test(head)) return 'xml';
	if (/^<(?:!doctype\s+html|html|head|body|div|span|p|a|table|form|meta|script)\b/i.test(head))
		return 'html';
	if (head[0] === '<') return 'xml';
	return fallback;
}

function mergeLines(lines: CodeLine[], sub: CodeLine[]) {
	if (!sub.length) return;
	for (const token of sub[0]) push(lines[lines.length - 1], token.text, token.kind);
	for (let index = 1; index < sub.length; index++) lines.push(sub[index]);
}

function appendLang(lines: CodeLine[], code: string, lang: CodeLang) {
	switch (lang) {
		case 'json':
			return tokenizeJsonInto(code, lines);
		case 'html':
		case 'xml':
			return tokenizeMarkupInto(code, lines);
		case 'css':
			return tokenizeCssInto(code, lines);
		case 'js':
			return tokenizeJsInto(code, lines);
		case 'yaml':
			return mergeLines(lines, highlightYaml(code));
		case 'shell':
			return mergeLines(lines, highlightShell(code));
		default:
			return mergeLines(lines, plainLines(code));
	}
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
	let mode: 'head' | 'headers' = 'head';
	let contentType: string | null = null;

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
			if (HEADER_LINE.test(raw)) mode = 'headers';
		}

		if (mode === 'headers' && raw.trim()) {
			const header = HEADER_LINE.exec(raw);
			if (header && CONTENT_TYPE.test(header[1])) contentType = header[4];
			put(headerLine(raw));
			continue;
		}

		put(raw ? [{ text: raw, kind: 'text' }] : []);
		if (mode !== 'headers') continue;

		if (index + 1 < source.length) {
			const body = source.slice(index + 1).join('\n');
			lines.push([]);
			appendLang(lines, body, langForContentType(contentType, body));
		}
		return lines;
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

const BODY_SEPARATOR = /\r?\n\r?\n/;

function indentMarkup(code: string): string | null {
	const flat = code.replace(/>\s*\n\s*</g, '><').replace(/>\s*</g, '>\n<');
	const out: string[] = [];
	let depth = 0;
	for (const part of flat.split('\n')) {
		const line = part.trim();
		if (!line) continue;
		if (/^<\//.test(line)) depth = Math.max(0, depth - 1);
		out.push('  '.repeat(depth) + line);
		const open = /^<([\w:.-]+)/.exec(line);
		if (open && !/\/>$/.test(line) && !new RegExp(`</${open[1]}\\s*>$`, 'i').test(line)) {
			if (!VOID_TAGS.has(open[1].toLowerCase())) depth++;
		}
	}
	return out.length ? out.join('\n') : null;
}

function indentCss(code: string): string | null {
	const flat = code.replace(/\s+/g, ' ').trim();
	if (!flat) return null;
	const out: string[] = [];
	let line = '';
	let depth = 0;
	const flush = () => {
		let value = line.trim();
		if (depth > 0) value = value.replace(/^([-\w]+)\s*:\s*/, '$1: ');
		if (value) out.push('  '.repeat(depth) + value);
		line = '';
	};
	for (const char of flat) {
		if (char === '{') {
			line += ' {';
			flush();
			depth++;
		} else if (char === '}') {
			flush();
			depth = Math.max(0, depth - 1);
			out.push('  '.repeat(depth) + '}');
		} else if (char === ';') {
			line += ';';
			flush();
		} else line += char;
	}
	flush();
	return out.length ? out.join('\n') : null;
}

function formatBody(code: string, lang: CodeLang): string | null {
	switch (lang) {
		case 'json':
			try {
				return JSON.stringify(JSON.parse(code), null, 2);
			} catch {
				return null;
			}
		case 'html':
		case 'xml':
			return indentMarkup(code);
		case 'css':
			return indentCss(code);
		default:
			return null;
	}
}

export function prettify(code: string, lang: CodeLang): string | null {
	if (!code || code.length > MAX_HIGHLIGHT_BYTES) return null;
	try {
		if (lang !== 'http') {
			const out = formatBody(code, lang);
			return out && out !== code ? out : null;
		}
		const match = BODY_SEPARATOR.exec(code);
		if (!match) return null;
		const cut = match.index + match[0].length;
		const head = code.slice(0, cut);
		const body = code.slice(cut);
		if (!body.trim()) return null;
		const type = /^content-type:[ \t]*(.*)$/im.exec(head)?.[1]?.trim() ?? null;
		const out = formatBody(body, langForContentType(type, body));
		return out && out !== body ? head + out : null;
	} catch {
		return null;
	}
}

export function highlight(code: string, lang: CodeLang = 'text'): CodeLine[] {
	if (!code) return [];
	if (code.length > MAX_HIGHLIGHT_BYTES) return plainLines(code);
	try {
		switch (lang) {
			case 'yaml':
				return highlightYaml(code);
			case 'http':
				return highlightHttp(code);
			case 'shell':
				return highlightShell(code);
			case 'text':
				return plainLines(code);
			default: {
				const lines: CodeLine[] = [[]];
				appendLang(lines, code, lang);
				return lines;
			}
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

export interface CodeSearch {
	lines: CodeLine[];
	hits: number;
}

export function applySearch(lines: CodeLine[], term: string): CodeSearch {
	const needle = term.toLowerCase();
	if (!needle) return { lines, hits: 0 };

	let hits = 0;
	const marked = lines.map((line) => {
		const out: CodeLine = [];
		for (const token of line) {
			const lower = token.text.toLowerCase();
			let cursor = 0;
			for (;;) {
				const at = lower.indexOf(needle, cursor);
				if (at < 0) {
					if (cursor < token.text.length) out.push({ ...token, text: token.text.slice(cursor) });
					break;
				}
				if (at > cursor) out.push({ ...token, text: token.text.slice(cursor, at) });
				out.push({ ...token, text: token.text.slice(at, at + needle.length), hit: hits++ });
				cursor = at + needle.length;
			}
		}
		return out;
	});
	return { lines: marked, hits };
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
