const COMPACT = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

export function compactCount(n: number): string {
	return Math.abs(n) < 10_000 ? n.toLocaleString() : COMPACT.format(n);
}
