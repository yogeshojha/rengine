import type { CodeLang } from './code-highlight';

const HTML_HINT = /<\/?[a-z][\s\S]*>/i;
const JSON_HINT = /^\s*[[{]/;
const JS_HINT = /\b(const|let|var|function|=>|return|import|export)\b|[;{}]\s*$/m;
const CSS_HINT = /[.#]?[a-z-]+\s*\{[^}]*:[^}]*\}/i;

/** Best-effort language for a stored context window. */
export function contextLang(text: string | null | undefined): CodeLang {
	if (!text) return 'text';
	if (HTML_HINT.test(text)) return 'html';
	if (JSON_HINT.test(text)) return 'json';
	if (JS_HINT.test(text)) return 'js';
	if (CSS_HINT.test(text)) return 'css';
	return 'text';
}

export const META_LABELS: Record<string, string> = {
	alg: 'Algorithm',
	typ: 'Type',
	iss: 'Issuer',
	aud: 'Audience',
	exp: 'Expires',
	expired: 'Expired',
	domain: 'Domain',
	scheme: 'Scheme',
	username: 'Username',
	host: 'Host',
	port: 'Port',
	algorithm: 'Algorithm',
	complete: 'Complete'
};

export function metaLabel(key: string): string {
	return META_LABELS[key] ?? key;
}
