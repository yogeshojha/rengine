const BYTE_UNITS = ['B', 'KB', 'MB', 'GB'];

export function formatBytes(n: number | null | undefined): string {
	if (n == null) return '—';
	let value = n;
	let unit = 0;
	while (value >= 1024 && unit < BYTE_UNITS.length - 1) {
		value /= 1024;
		unit += 1;
	}
	return `${value < 10 && unit > 0 ? value.toFixed(1) : Math.round(value)} ${BYTE_UNITS[unit]}`;
}
