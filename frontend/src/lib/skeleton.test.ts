import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = join(import.meta.dirname, '..');

const LOADING_TEXT = /(?:^|>)\s*(?:Loading|Searching|Fetching)\b[^<{]*(?:<|$)/gm;
const PULSING_TEXT = /<span[^>]*\banimate-pulse\b[^>]*>\s*[A-Za-z]/g;
const RAW_ROWS = /\{#each Array\([^)]*\)[^}]*\}\s*(?:<[^>]*>\s*)*<Skeleton\b/g;

// spinners allowed: button affordances and app boot
const SPINNER_ALLOWED = new Set([
	'components/loading-button.svelte',
	'components/confirm-dialog.svelte',
	'components/search-bar.svelte',
	'components/scan-status-badge.svelte',
	'routes/+page.svelte',
	'routes/(app)/+layout.svelte',
	'routes/onboarding/+page.svelte'
]);

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (name === 'ui' && dir.endsWith('components')) continue;
		if (statSync(path).isDirectory()) walk(path, out);
		else if (name.endsWith('.svelte')) out.push(path);
	}
	return out;
}

function offenders(pattern: RegExp, filter?: (rel: string) => boolean): string[] {
	return walk(ROOT)
		.map((file) => ({ rel: file.slice(ROOT.length + 1), body: readFileSync(file, 'utf8') }))
		.filter((entry) => !filter || filter(entry.rel))
		.map((entry) => ({ rel: entry.rel, hits: entry.body.match(pattern) }))
		.filter((entry) => entry.hits)
		.map((entry) => `${entry.rel}: ${entry.hits?.[0].trim()}`);
}

describe('loading states', () => {
	it('never prints a sentence where a skeleton belongs', () => {
		expect(offenders(LOADING_TEXT, (rel) => !SPINNER_ALLOWED.has(rel))).toEqual([]);
	});

	it('never fakes a skeleton by pulsing text', () => {
		expect(offenders(PULSING_TEXT)).toEqual([]);
	});

	it('builds table skeletons from the table columns', () => {
		expect(offenders(RAW_ROWS, (rel) => rel.endsWith('-table.svelte'))).toEqual([]);
	});
});
