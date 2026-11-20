import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(join(import.meta.dirname, 'users-panel.svelte'), 'utf8');

describe('users panel', () => {
	it('opens the access keys of a user from the row menu', () => {
		expect(source).toMatch(/<DropdownMenu\.Item onSelect=\{\(\) => \(viewingKeys = user\)\}>/);
		expect(source).toContain('<UserAccessKeysDialog user={viewingKeys}');
	});
});
