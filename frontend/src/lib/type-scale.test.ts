import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { sourceFiles } from './test-utils/source-files';

const ROOT = join(import.meta.dirname, '..');
const APP_CSS = join(ROOT, 'app.css');
const ARBITRARY_SIZE = /\btext-\[[0-9.]+(?:px|rem|em)\]/g;
const PX_FONT_SIZE = /font-size:\s*\d+(?:\.\d+)?px/g;
const STYLE_BLOCK = /<style[^>]*>([\s\S]*?)<\/style>/g;

const rel = (file: string) => file.slice(ROOT.length + 1);

/** Drops every `@layer … { … }` block so only unlayered rules remain. */
function stripLayers(css: string): string {
	let out = '';
	let i = 0;
	while (i < css.length) {
		const at = css.indexOf('@layer', i);
		if (at === -1) break;
		const open = css.indexOf('{', at);
		const semi = css.indexOf(';', at);
		out += css.slice(i, at);
		if (open === -1 || (semi !== -1 && semi < open)) {
			i = semi === -1 ? css.length : semi + 1; // `@layer a, b;` statement
			continue;
		}
		let depth = 1;
		let j = open + 1;
		while (j < css.length && depth > 0) {
			if (css[j] === '{') depth++;
			else if (css[j] === '}') depth--;
			j++;
		}
		i = j;
	}
	return out + css.slice(i);
}

describe('type scale', () => {
	it('uses the named steps, never an arbitrary pixel size', () => {
		const offenders = sourceFiles(ROOT, /\.(svelte|ts)$/)
			.map((file) => ({ file, hits: readFileSync(file, 'utf8').match(ARBITRARY_SIZE) }))
			.filter((entry) => entry.hits)
			.map((entry) => `${rel(entry.file)}: ${entry.hits?.join(' ')}`);
		expect(offenders).toEqual([]);
	});

	it('keeps raw px font sizes out of scoped <style> blocks and app.css', () => {
		const offenders: string[] = [];
		for (const file of sourceFiles(ROOT, /\.svelte$/)) {
			for (const [, css] of readFileSync(file, 'utf8').matchAll(STYLE_BLOCK)) {
				const hits = css.match(PX_FONT_SIZE);
				if (hits) offenders.push(`${rel(file)}: ${hits.join(' ')}`);
			}
		}
		const appHits = readFileSync(APP_CSS, 'utf8').match(PX_FONT_SIZE);
		if (appHits) offenders.push(`app.css: ${appHits.join(' ')}`);
		expect(offenders).toEqual([]);
	});

	it('layers element rules for body and headings so utilities win', () => {
		const css = stripLayers(readFileSync(APP_CSS, 'utf8').replace(/\/\*[\s\S]*?\*\//g, ''));
		const unlayered = css.match(/(?:^|[,}\s])(?:body|h[1-6])\s*(?=[,{])/g) ?? [];
		expect(unlayered.map((s) => s.trim().replace(/^[,}]/, ''))).toEqual([]);
	});
});
