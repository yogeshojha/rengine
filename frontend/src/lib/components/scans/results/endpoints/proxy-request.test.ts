import { describe, expect, it } from 'vitest';
import { isEdited, lf, withBreaksOf } from './proxy-request';

const CRLF = 'POST /u HTTP/1.1\r\nHost: h\r\n\r\n--b\r\nname="a"\r\n\r\n1\r\n--b--\r\n';

describe('edited request text', () => {
	it('holds LF line breaks', () => {
		expect(lf('a\r\nb\rc\nd')).toBe('a\nb\nc\nd');
	});

	it('reads an unchanged draft as unedited', () => {
		expect(isEdited(lf(CRLF), CRLF)).toBe(false);
		expect(isEdited(`${lf(CRLF)}x`, CRLF)).toBe(true);
	});

	it('gives a CRLF request its CRLF back', () => {
		expect(withBreaksOf(lf(CRLF), CRLF)).toBe(CRLF);
		expect(withBreaksOf('GET / HTTP/1.1\nHost: h\nX-Test: 1\n\n', CRLF)).toBe(
			'GET / HTTP/1.1\r\nHost: h\r\nX-Test: 1\r\n\r\n'
		);
	});

	it('keeps LF when the loaded body had bare LF', () => {
		const loaded = 'POST /j HTTP/1.1\r\nHost: h\r\n\r\n{\n  "a": 1\n}';
		expect(withBreaksOf(lf(loaded), loaded)).toBe(lf(loaded));
	});
});
