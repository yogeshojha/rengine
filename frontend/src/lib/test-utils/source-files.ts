import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

export function sourceFiles(root: string, pattern: RegExp): string[] {
	const out: string[] = [];
	const walk = (dir: string) => {
		for (const name of readdirSync(dir)) {
			const path = join(dir, name);
			if (name === 'ui' && dir.endsWith('components')) continue;
			if (statSync(path).isDirectory()) walk(path);
			else if (pattern.test(name)) out.push(path);
		}
	};
	walk(root);
	return out;
}
