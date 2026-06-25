export function parseCsv(value: string): string[] {
	return value
		.split(',')
		.map((s) => s.trim())
		.filter(Boolean);
}

export function parseLines(value: string): string[] {
	return value
		.split(/\r?\n/)
		.map((s) => s.trim())
		.filter(Boolean);
}
