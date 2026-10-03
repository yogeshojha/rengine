import { describe, expect, it } from 'vitest';
import { canChangeNote } from './subject';

describe('canChangeNote', () => {
	const note = { created_by: 'author' };

	it('lets the author and an administrator edit', () => {
		expect(canChangeNote(note, { id: 'author', is_superuser: false })).toBe(true);
		expect(canChangeNote(note, { id: 'admin', is_superuser: true })).toBe(true);
	});

	it('keeps another member out', () => {
		expect(canChangeNote(note, { id: 'member', is_superuser: false })).toBe(false);
		expect(canChangeNote(note, null)).toBe(false);
	});
});
