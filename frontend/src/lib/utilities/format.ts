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

/** A duration as `850ms`, `1.2s`, `45s`, `3m 12s` or `1h 4m`. */
export function formatMilliseconds(ms: number | null | undefined): string {
	if (ms == null || !Number.isFinite(ms)) return '';
	const whole = Math.max(0, Math.round(ms));
	if (whole < 1000) return `${whole}ms`;
	const tenths = Math.round(whole / 100) / 10;
	if (tenths < 10) return `${tenths}s`;
	const total = Math.round(whole / 1000);
	if (total < 60) return `${total}s`;
	const minutes = Math.floor(total / 60);
	if (minutes < 60) return total % 60 ? `${minutes}m ${total % 60}s` : `${minutes}m`;
	const hours = Math.floor(minutes / 60);
	return minutes % 60 ? `${hours}h ${minutes % 60}m` : `${hours}h`;
}

export function formatSeconds(seconds: number | null | undefined): string {
	return seconds == null ? '' : formatMilliseconds(seconds * 1000);
}
