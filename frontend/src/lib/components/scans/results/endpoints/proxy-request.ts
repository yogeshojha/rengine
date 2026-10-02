const BREAK = /\r\n?/g;
const BARE_LF = /(^|[^\r])\n/;

/** The text with LF line breaks. */
export function lf(text: string): string {
	return text.replace(BREAK, '\n');
}

/** True when the editor holds something other than the loaded request. */
export function isEdited(draft: string, loaded: string): boolean {
	return lf(draft) !== lf(loaded);
}

/** The draft with the line breaks of the request it was loaded from. */
export function withBreaksOf(draft: string, loaded: string): string {
	const text = lf(draft);
	return loaded.includes('\r\n') && !BARE_LF.test(loaded) ? text.replace(/\n/g, '\r\n') : text;
}
