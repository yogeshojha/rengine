import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { sourceFiles } from './test-utils/source-files';

const ROOT = join(import.meta.dirname, '..');
const RETIRED = [/\bweb hosts?\b/gi, /\blive hosts?\b/gi];

describe('glossary', () => {
	it('names a probed host a web asset', () => {
		const offenders = sourceFiles(ROOT, /^(?!.*\.test\.ts$).*\.(svelte|ts)$/).flatMap((file) => {
			const text = readFileSync(file, 'utf8');
			const hits = RETIRED.flatMap((re) => text.match(re) ?? []);
			return hits.length ? [`${file.slice(ROOT.length + 1)}: ${hits.join(' ')}`] : [];
		});
		expect(offenders).toEqual([]);
	});
});
