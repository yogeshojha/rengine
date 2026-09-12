import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = join(import.meta.dirname, '..');
const RETIRED = [/\bweb hosts?\b/gi, /\blive hosts?\b/gi];

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (name === 'ui' && dir.endsWith('components')) continue;
		if (statSync(path).isDirectory()) walk(path, out);
		else if (/\.(svelte|ts)$/.test(name) && !name.endsWith('.test.ts')) out.push(path);
	}
	return out;
}

describe('glossary', () => {
	it('names a probed host a web asset', () => {
		const offenders = walk(ROOT).flatMap((file) => {
			const text = readFileSync(file, 'utf8');
			const hits = RETIRED.flatMap((re) => text.match(re) ?? []);
			return hits.length ? [`${file.slice(ROOT.length + 1)}: ${hits.join(' ')}`] : [];
		});
		expect(offenders).toEqual([]);
	});
});
