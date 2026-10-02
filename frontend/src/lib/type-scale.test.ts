import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { sourceFiles } from './test-utils/source-files';

const ROOT = join(import.meta.dirname, '..');
const ARBITRARY_SIZE = /\btext-\[[0-9.]+(?:px|rem|em)\]/g;

describe('type scale', () => {
	it('uses the named steps, never an arbitrary pixel size', () => {
		const offenders = sourceFiles(ROOT, /\.(svelte|ts)$/)
			.map((file) => ({ file, hits: readFileSync(file, 'utf8').match(ARBITRARY_SIZE) }))
			.filter((entry) => entry.hits)
			.map((entry) => `${entry.file.slice(ROOT.length + 1)}: ${entry.hits?.join(' ')}`);
		expect(offenders).toEqual([]);
	});
});
