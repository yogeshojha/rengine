import { describe, expect, it } from 'vitest';
import { csvCell } from './csv';

describe('csvCell', () => {
	it('defuses a formula lead', () => {
		expect(csvCell('=HYPERLINK("http://x","y")')).toBe('"\'=HYPERLINK(""http://x"",""y"")"');
		expect(csvCell('+1')).toBe("'+1");
		expect(csvCell('-2')).toBe("'-2");
		expect(csvCell('@SUM(A1)')).toBe("'@SUM(A1)");
		expect(csvCell('\tcmd')).toBe("'\tcmd");
	});

	it('quotes a separator, a quote or a line break', () => {
		expect(csvCell('a,b')).toBe('"a,b"');
		expect(csvCell('say "hi"')).toBe('"say ""hi"""');
		expect(csvCell('a\nb')).toBe('"a\nb"');
	});

	it('leaves a plain value alone', () => {
		expect(csvCell('example.com')).toBe('example.com');
		expect(csvCell('')).toBe('');
	});
});
