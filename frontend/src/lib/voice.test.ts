import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = join(import.meta.dirname, '..');

// ---------- tells ----------
const REGISTER =
	/\b(seamless(ly)?|robust|powerful|leverage|unlock|elevate|comprehensive|effortless(ly)?|supercharge|streamline|cutting-edge|best-in-class|empower|holistic|dive in|at a glance)\b/i;
const ADDRESS = /\b(you|your|you're|we|we'll|our|let's|please)\b/i;
const SCOPE_NARRATION =
	/\b(in this project|across all targets|of each target|from the latest (scan|run|covering run))\b/i;
// a description may decode a visual encoding; that is not a restatement
const ENCODING = /\b(sized|tinted|coloured|colored|ranked|ordered|scaled|shaded) by\b/i;

const STOP = new Set([
	'a',
	'an',
	'and',
	'the',
	'of',
	'on',
	'in',
	'by',
	'for',
	'to',
	'from',
	'with',
	'or',
	'at',
	'as',
	'is',
	'are',
	'its',
	'this',
	'that',
	'each',
	'per',
	'all',
	'no',
	'not',
	'one',
	'every'
]);

const words = (s: string) =>
	s
		.toLowerCase()
		.replace(/[^a-z0-9\s]/g, ' ')
		.split(/\s+/)
		.filter((w) => w.length > 2 && !STOP.has(w));

const stem = (w: string) => w.slice(0, 5);

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (name === 'ui' && dir.endsWith('components')) continue;
		if (statSync(path).isDirectory()) walk(path, out);
		else if (/\.svelte$/.test(name)) out.push(path);
	}
	return out;
}

const files = walk(ROOT).map((path) => ({
	name: path.slice(ROOT.length + 1),
	text: readFileSync(path, 'utf8')
}));

// an informational heading describes; an action heading (confirm, empty state)
// states a consequence, which is not a restatement
const INFORMATIONAL = /<(Widget|PanelHead)\b([\s\S]{0,400}?)\/?>/g;

function pairs(text: string): { title: string; description: string }[] {
	const found: { title: string; description: string }[] = [];
	for (const tag of text.matchAll(INFORMATIONAL)) {
		const title = tag[2].match(/title=\{?"([^"{}]{2,80})"/);
		const description = tag[2].match(/description=\{?"([^"]{4,200})"/);
		if (title && description) found.push({ title: title[1], description: description[1] });
	}
	return found;
}

/** the muted paragraph that sits directly under a page heading. */
function subtitles(text: string): string[] {
	const re =
		/<h1[^>]*>[\s\S]{0,200}?<\/h1>\s*<p[^>]*text-muted-foreground[^>]*>([\s\S]{0,300}?)<\/p>/g;
	return [...text.matchAll(re)].map((m) => m[1].replace(/\s+/g, ' ').trim());
}

/** every string a Widget or PanelHead shows as a description. */
function descriptions(text: string): string[] {
	const re = /description=\{?"([^"]{4,200})"/g;
	return [...text.matchAll(re)].map((m) => m[1]);
}

describe('voice', () => {
	it('keeps LLM register out of copy', () => {
		const offenders = files.flatMap(({ name, text }) =>
			[...descriptions(text), ...subtitles(text)]
				.filter((s) => REGISTER.test(s))
				.map((s) => `${name}: ${s}`)
		);
		expect(offenders).toEqual([]);
	});

	it('does not address the reader', () => {
		const offenders = files.flatMap(({ name, text }) =>
			[...descriptions(text), ...subtitles(text)]
				.filter((s) => ADDRESS.test(s))
				.map((s) => `${name}: ${s}`)
		);
		expect(offenders).toEqual([]);
	});

	it('does not narrate scope a control already shows', () => {
		const offenders = files.flatMap(({ name, text }) =>
			[...descriptions(text), ...subtitles(text)]
				.filter((s) => SCOPE_NARRATION.test(s))
				.map((s) => `${name}: ${s}`)
		);
		expect(offenders).toEqual([]);
	});

	it('does not restate a title in its own description', () => {
		const offenders = files.flatMap(({ name, text }) =>
			pairs(text)
				.filter(({ title, description }) => {
					if (ENCODING.test(description)) return false;
					const t = words(title);
					if (!t.length) return false;
					const d = new Set(words(description).map(stem));
					return t.every((w) => d.has(stem(w)));
				})
				.map(({ title, description }) => `${name}: "${title}" / "${description}"`)
		);
		expect(offenders).toEqual([]);
	});
});
