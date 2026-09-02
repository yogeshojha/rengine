export function parseCsv(value: string): string[] {
	return value
		.split(',')
		.map((s) => s.trim())
		.filter(Boolean);
}
