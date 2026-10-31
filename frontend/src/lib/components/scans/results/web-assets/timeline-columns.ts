import type { TableColumn } from '../table/columns';
import { RenderSort, TimelineSort } from '$lib/config/timeline';

export const TIMELINE_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'name',
		label: 'Host',
		sort: TimelineSort.NAME,
		width: 'min-w-0 flex-[2] contain-inline-size sm:min-w-64'
	}
];

export const TIMELINE_COLUMNS: TableColumn[] = [
	{ key: 'strip', label: 'Scans', width: 'shrink-0' },
	{ key: 'state', label: 'Now', sort: TimelineSort.STATUS, width: 'w-32 shrink-0' },
	{ key: 'first', label: 'First seen', sort: TimelineSort.FIRST_SEEN, width: 'w-28 shrink-0' },
	{
		key: 'changes',
		label: 'Changes',
		sort: TimelineSort.CHANGES,
		align: 'right',
		width: 'w-16 shrink-0'
	},
	{ key: 'last', label: 'Last change', sort: TimelineSort.LAST_CHANGE, width: 'w-56 shrink-0' }
];

export const RENDER_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'name',
		label: 'Host',
		sort: RenderSort.NAME,
		width: 'min-w-0 flex-[2] contain-inline-size sm:min-w-64'
	}
];

export const RENDER_COLUMNS: TableColumn[] = [
	{ key: 'strip', label: 'Scans', width: 'shrink-0' },
	{ key: 'now', label: 'Now', sort: RenderSort.STATUS, width: 'w-28 shrink-0' },
	{
		key: 'first',
		label: 'First screenshot',
		sort: RenderSort.FIRST_CAPTURED,
		width: 'w-28 shrink-0'
	},
	{
		key: 'changes',
		label: 'Changes',
		sort: RenderSort.CHANGES,
		align: 'right',
		width: 'w-16 shrink-0'
	},
	{ key: 'last', label: 'Last change', sort: RenderSort.LAST_CHANGE, width: 'w-56 shrink-0' }
];

export const CELL_PX = 10;
export const CELL_GAP_PX = 2;

export function stripWidth(cells: number): number {
	return Math.max(0, cells * (CELL_PX + CELL_GAP_PX) - CELL_GAP_PX);
}

export function cellLeft(index: number): number {
	return index * (CELL_PX + CELL_GAP_PX);
}
