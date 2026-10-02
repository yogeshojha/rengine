import { MAX_NOTE_TAG_CHARS, MAX_NOTE_TAGS, NOTE_TAG_PUNCTUATION } from '$lib/types/note';

const LETTER_OR_DIGIT = /[\p{L}\p{M}\p{N}]/u;

export const TOO_MANY_TAGS = `A note takes at most ${MAX_NOTE_TAGS} tags.`;

/** A tag as stored: trimmed, no leading #, lowercase, whitespace as hyphens. */
export function noteTag(value: string): string {
	return value.trim().replace(/^#+/, '').trim().toLowerCase().replace(/\s+/g, '-');
}

/** Why the server refuses a stored-form tag, or null. */
export function noteTagError(tag: string): string | null {
	const chars = [...tag];
	if (chars.length > MAX_NOTE_TAG_CHARS)
		return `Tags are at most ${MAX_NOTE_TAG_CHARS} characters.`;
	if (!chars.every((ch) => LETTER_OR_DIGIT.test(ch) || NOTE_TAG_PUNCTUATION.includes(ch)))
		return `Tag "${tag}" has a character outside letters, digits, dot, underscore, hyphen and colon.`;
	return null;
}

/** Typed text split on commas into stored-form tags, blanks dropped. */
export function splitNoteTags(text: string): string[] {
	return [...new Set(text.split(/[,\n]/).map(noteTag).filter(Boolean))];
}
