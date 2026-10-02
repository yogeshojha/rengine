import { describe, expect, it } from 'vitest';
import { MAX_NOTE_TAG_CHARS } from '$lib/types/note';
import { noteTag, noteTagError, splitNoteTags } from './tags';

describe('note tags', () => {
	it('stores the typed name the way the server does', () => {
		expect(noteTag('IDOR')).toBe('idor');
		expect(noteTag('  #Auth ')).toBe('auth');
		expect(noteTag('##api:v2')).toBe('api:v2');
		expect(noteTag('#  sql   injection ')).toBe('sql-injection');
		expect(noteTag('#')).toBe('');
	});

	it('splits typed text on commas', () => {
		expect(splitNoteTags('IDOR, #auth,,idor\nxss')).toEqual(['idor', 'auth', 'xss']);
		expect(splitNoteTags(' , ')).toEqual([]);
	});

	it('takes letters, digits and four marks', () => {
		for (const ok of ['café', 'नेपाल', 'a.b_c-d:e', 'x'.repeat(MAX_NOTE_TAG_CHARS)])
			expect(noteTagError(ok)).toBeNull();
		for (const bad of ['a/b', '<script>', '50%', 'a#b'])
			expect(noteTagError(bad)).toMatch(/has a character outside/);
		expect(noteTagError('x'.repeat(MAX_NOTE_TAG_CHARS + 1))).toMatch(/at most 32 characters/);
	});
});
