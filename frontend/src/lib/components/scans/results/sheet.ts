import type { IconComponent } from '$lib/config/icons';
import { keyTaken, topLayer } from '$lib/utilities/layers';

export const SHEET_ROW = 'grid grid-cols-[8.5rem_minmax(0,1fr)] items-start gap-3 py-2';
export const SHEET_ROW_TIGHT = 'grid grid-cols-[7.5rem_minmax(0,1fr)] items-start gap-3 py-2';
export const SHEET_DT = 'pt-0.5 text-xs text-muted-foreground';
// pt-2.5 centres the first row on the close button
export const SHEET_HEAD = 'gap-2 border-b px-5 pt-2.5 pb-4';

export interface SheetAction {
	label: string;
	icon: IconComponent;
	run?: () => void;
	href?: string;
}

export function sheetStep(e: KeyboardEvent, open: boolean, onStep?: (dir: 1 | -1) => void): void {
	if (!open || e.metaKey || e.ctrlKey || e.altKey) return;
	if (keyTaken(e.target)) return;
	if (topLayer()?.getAttribute('data-slot') !== 'sheet-content') return;
	if (e.key === 'ArrowDown' || e.key === 'j') {
		e.preventDefault();
		onStep?.(1);
	} else if (e.key === 'ArrowUp' || e.key === 'k') {
		e.preventDefault();
		onStep?.(-1);
	}
}
