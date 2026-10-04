const COMPACT = new Intl.NumberFormat('en-US', { notation: 'compact' });

const COMPACT_FROM = 10_000;
export const COMPACT_FROM_SHORT = 1_000;

/** A count as `9,999`, then `12K` and `1.2M` from `threshold` up. */
export function compactCount(n: number, threshold = COMPACT_FROM): string {
	return Math.abs(n) < threshold ? Math.round(n).toLocaleString() : COMPACT.format(n);
}
