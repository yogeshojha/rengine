import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = join(import.meta.dirname, '..');
const ARBITRARY_SIZE = /\btext-\[[0-9.]+(?:px|rem|em)\]/g;

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (name === 'ui' && dir.endsWith('components')) continue;
		if (statSync(path).isDirectory()) walk(path, out);
		else if (/\.(svelte|ts)$/.test(name)) out.push(path);
	}
	return out;
}

describe('type scale', () => {
	it('uses the named steps, never an arbitrary pixel size', () => {
		const offenders = walk(ROOT)
			.map((file) => ({ file, hits: readFileSync(file, 'utf8').match(ARBITRARY_SIZE) }))
			.filter((entry) => entry.hits)
			.map((entry) => `${entry.file.slice(ROOT.length + 1)}: ${entry.hits?.join(' ')}`);
		expect(offenders).toEqual([]);
	});
});
