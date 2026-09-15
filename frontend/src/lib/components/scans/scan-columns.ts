import type { TableColumn } from './results/table/columns';

export const SCAN_WIDTHS = {
	engine: 'hidden w-[150px] shrink-0 lg:block',
	status: 'flex w-[120px] shrink-0',
	results: 'hidden w-[220px] shrink-0 xl:flex',
	duration: 'hidden w-[80px] shrink-0 justify-end sm:flex',
	started: 'hidden w-[120px] shrink-0 justify-end sm:flex',
	actions: 'w-8 shrink-0'
} as const;

export function scanSkeletonColumns(targetId?: string | null): TableColumn[] {
	const cols: TableColumn[] = [
		{ key: 'name', label: targetId ? 'Engine' : 'Target', width: 'min-w-0 flex-1' }
	];
	if (!targetId) cols.push({ key: 'engine', label: 'Engine', width: SCAN_WIDTHS.engine });
	cols.push(
		{ key: 'status', label: 'Status', width: SCAN_WIDTHS.status },
		{ key: 'results', label: 'Results', width: SCAN_WIDTHS.results },
		{ key: 'duration', label: 'Duration', width: SCAN_WIDTHS.duration, align: 'right' },
		{ key: 'started', label: 'Started', width: SCAN_WIDTHS.started, align: 'right' },
		{ key: 'actions', label: '', width: SCAN_WIDTHS.actions }
	);
	return cols;
}
