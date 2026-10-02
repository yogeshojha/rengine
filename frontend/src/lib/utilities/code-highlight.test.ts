import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { highlight } from './code-highlight';
import { TOKEN_STYLES, tokenRanges } from './code-theme';

function tokens(code: string): [string, string][] {
	return highlight(code, 'http')
		.flat()
		.filter((token) => token.text.trim())
		.map((token) => [token.text.trim(), token.kind]);
}

function line(code: string, at: number): [string, string][] {
	return highlight(code, 'http')
		[at].filter((token) => token.text.trim())
		.map((token) => [token.text.trim(), token.kind]);
}

const REQUEST = [
	'POST /api/login?next=%2Fhome&debug HTTP/1.1',
	'Host: example.com',
	'Cookie: session=abc==; theme=dark',
	'Content-Type: application/json',
	'Content-Length: 27',
	'Referer: https://example.com/a',
	'',
	'{"user":"admin","n":1,"ok":true}'
].join('\r\n');

describe('http highlighting', () => {
	it('splits the request line into method, path, query and version', () => {
		expect(line(REQUEST, 0)).toEqual([
			['POST', 'keyword'],
			['/api/login', 'fn'],
			['?', 'punct'],
			['next', 'attr'],
			['=', 'punct'],
			['%2Fhome', 'string'],
			['&', 'punct'],
			['debug', 'attr'],
			['HTTP/1.1', 'meta']
		]);
	});

	it('reads a request target that holds spaces', () => {
		expect(line('GET /a b HTTP/1.1', 0)).toEqual([
			['GET', 'keyword'],
			['/a b', 'fn'],
			['HTTP/1.1', 'meta']
		]);
		expect(line('GET / HTTP/2', 0)).toEqual([
			['GET', 'keyword'],
			['/', 'fn'],
			['HTTP/2', 'meta']
		]);
	});

	it('colours header names, values, cookies, lengths and links', () => {
		expect(line(REQUEST, 1)).toEqual([
			['Host', 'key'],
			[':', 'punct'],
			['example.com', 'string']
		]);
		expect(line(REQUEST, 2)).toEqual([
			['Cookie', 'key'],
			[':', 'punct'],
			['session', 'attr'],
			['=', 'punct'],
			['abc==', 'string'],
			[';', 'punct'],
			['theme', 'attr'],
			['=', 'punct'],
			['dark', 'string']
		]);
		expect(line('GET / HTTP/1.1\nCookie: ***', 1)).toEqual([
			['Cookie', 'key'],
			[':', 'punct'],
			['***', 'string']
		]);
		expect(line(REQUEST, 4)).toContainEqual(['27', 'number']);
		expect(line(REQUEST, 5)).toContainEqual(['https://example.com/a', 'link']);
	});

	it('colours a JSON body', () => {
		expect(line(REQUEST, 7)).toEqual([
			['{', 'punct'],
			['"user"', 'key'],
			[':', 'punct'],
			['"admin"', 'string'],
			[',', 'punct'],
			['"n"', 'key'],
			[':', 'punct'],
			['1', 'number'],
			[',', 'punct'],
			['"ok"', 'key'],
			[':', 'punct'],
			['true', 'atom'],
			['}', 'punct']
		]);
	});

	it('colours a form body, declared or not', () => {
		const declared =
			'POST / HTTP/1.1\nContent-Type: application/x-www-form-urlencoded\n\na=1&b=x%20y';
		expect(tokens(declared).slice(-7)).toEqual([
			['a', 'attr'],
			['=', 'punct'],
			['1', 'string'],
			['&', 'punct'],
			['b', 'attr'],
			['=', 'punct'],
			['x%20y', 'string']
		]);
		expect(line('POST / HTTP/1.1\nHost: h\n\nq=1', 3)).toEqual([
			['q', 'attr'],
			['=', 'punct'],
			['1', 'string']
		]);
		expect(line('POST / HTTP/1.1\nHost: h\n\nplain words', 3)).toEqual([['plain words', 'text']]);
	});

	it('colours a multipart body', () => {
		const body = [
			'POST /u HTTP/1.1',
			'Content-Type: multipart/form-data; boundary=XB',
			'',
			'--XB',
			'Content-Disposition: form-data; name="file"; filename="a.txt"',
			'',
			'hello',
			'--XB--'
		].join('\r\n');
		expect(line(body, 3)).toEqual([['--XB', 'meta']]);
		expect(line(body, 4)).toEqual([
			['Content-Disposition', 'key'],
			[':', 'punct'],
			['form-data', 'string'],
			[';', 'punct'],
			['name', 'attr'],
			['=', 'punct'],
			['"file"', 'string'],
			[';', 'punct'],
			['filename', 'attr'],
			['=', 'punct'],
			['"a.txt"', 'string']
		]);
		expect(line(body, 6)).toEqual([['hello', 'text']]);
		expect(line(body, 7)).toEqual([['--XB--', 'meta']]);
	});

	it('colours the status line and Set-Cookie attributes', () => {
		const response = 'HTTP/1.1 404 Not Found\nSet-Cookie: sid=1; Path=/; HttpOnly\n\n';
		expect(line(response, 0)).toEqual([
			['HTTP/1.1', 'meta'],
			['404 Not Found', 'warn']
		]);
		expect(line(response, 1)).toEqual([
			['Set-Cookie', 'key'],
			[':', 'punct'],
			['sid', 'attr'],
			['=', 'punct'],
			['1', 'string'],
			[';', 'punct'],
			['Path', 'meta'],
			['=', 'punct'],
			['/', 'string'],
			[';', 'punct'],
			['HttpOnly', 'meta']
		]);
	});

	it('spells the input back exactly', () => {
		const samples = [
			REQUEST,
			REQUEST.replace(/\r\n/g, '\n'),
			'GET /x?a=1&&b= HTTP/1.1\r\nCookie: ; a\r\n\r\n',
			'POST / HTTP/1.1\nContent-Type: multipart/form-data; boundary="q"\n\n--q\nX: 1\n\nv\n--q--\n',
			'not a request\nat all'
		];
		for (const sample of samples) {
			const text = highlight(sample, 'http')
				.map((tokens) => tokens.map((token) => token.text).join(''))
				.join('\n');
			expect(text).toBe(sample);
		}
	});
});

describe('editor token ranges', () => {
	it('maps tokens to document offsets', () => {
		const doc = 'GET /a HTTP/1.1\nHost: h';
		const ranges = tokenRanges(highlight(doc, 'http'), doc.length);
		expect(ranges?.map((r) => [doc.slice(r.from, r.to), r.kind])).toEqual([
			['GET', 'keyword'],
			['/a', 'fn'],
			['HTTP/1.1', 'meta'],
			['Host', 'key'],
			[':', 'punct'],
			['h', 'string']
		]);
	});

	it('refuses tokens that do not spell the document', () => {
		expect(tokenRanges(highlight('GET / HTTP/1.1', 'http'), 3)).toBeNull();
	});
});

describe('code palette', () => {
	it('matches the code-block token rules', () => {
		const source = readFileSync(
			new URL('../components/code-block.svelte', import.meta.url),
			'utf8'
		);
		const rules = new Map<string, Record<string, string>>();
		const rule = /((?:\.cb-code :global\(\.t-[a-z]+\),?\s*)+)\{([^}]*)\}/g;
		for (const [, selectors, body] of source.matchAll(rule)) {
			const style = Object.fromEntries(
				body
					.split(';')
					.map((part) => part.trim())
					.filter(Boolean)
					.map((part) => {
						const at = part.indexOf(':');
						const name = part
							.slice(0, at)
							.trim()
							.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
						return [name, part.slice(at + 1).trim()];
					})
			);
			for (const [, kind] of selectors.matchAll(/\.t-([a-z]+)/g)) rules.set(kind, style);
		}
		expect(Object.fromEntries(rules)).toEqual(TOKEN_STYLES);
	});
});
