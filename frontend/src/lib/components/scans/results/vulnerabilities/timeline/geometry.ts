import type { TimelineScan } from '$lib/types/timeline';
import { formatMonthDay } from '$lib/utilities/dates';

export const TRACK_PX = 560;
export const MIN_COLUMN_PX = 10;
export const LABEL_PX = 44;

export function trackWidth(columns: number): number {
	return Math.max(TRACK_PX, columns * MIN_COLUMN_PX);
}

export function columnWidth(columns: number, width = trackWidth(columns)): number {
	return columns ? width / columns : width;
}

export function columnLeft(index: number, columns: number, width = trackWidth(columns)): number {
	return index * columnWidth(columns, width);
}

export function columnAt(x: number, columns: number, width = trackWidth(columns)): number {
	if (!columns) return -1;
	return Math.min(columns - 1, Math.max(0, Math.floor(x / columnWidth(columns, width))));
}

export interface AxisLabel {
	index: number;
	align: 'start' | 'center' | 'end';
	x: number;
	text: string;
}

/** The viewed run, the first run, then every few runs from the right, each clear of the others. */
export function axisLabels(scans: TimelineScan[], width: number): AxisLabel[] {
	const n = scans.length;
	if (!n) return [];
	const col = columnWidth(n, width);
	const every = n > 30 ? 8 : n > 8 ? 4 : 2;
	const placed: { index: number; align: AxisLabel['align']; span: [number, number] }[] = [];
	const anchor = (i: number, align: AxisLabel['align']) =>
		columnLeft(i, n, width) + (align === 'start' ? 0 : align === 'end' ? col : col / 2);
	const span = (i: number, align: AxisLabel['align']): [number, number] => {
		const x = anchor(i, align);
		if (align === 'start') return [x, x + LABEL_PX];
		if (align === 'end') return [x - LABEL_PX, x];
		return [x - LABEL_PX / 2, x + LABEL_PX / 2];
	};
	const place = (index: number, align: AxisLabel['align']) => {
		const next = span(index, align);
		if (placed.some((p) => next[0] < p.span[1] + 6 && p.span[0] < next[1] + 6)) return;
		placed.push({ index, align, span: next });
	};
	place(n - 1, 'end');
	if (n > 1) place(0, 'start');
	for (let i = n - 1 - every; i > 0; i -= every) place(i, 'center');
	return placed
		.sort((a, b) => a.index - b.index)
		.map((p) => ({
			index: p.index,
			align: p.align,
			x: anchor(p.index, p.align),
			text: formatMonthDay(scans[p.index].started_at ?? '')
		}));
}

export function shiftClass(align: AxisLabel['align']): string {
	if (align === 'start') return '';
	return align === 'end' ? '-translate-x-full' : '-translate-x-1/2';
}

export function dayCount(days: number): string {
	return days === 1 ? '1 day' : `${days} days`;
}
