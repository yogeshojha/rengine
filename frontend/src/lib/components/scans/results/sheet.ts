export const SHEET_ROW = 'grid grid-cols-[8.5rem_1fr] items-start gap-3 py-2';
export const SHEET_ROW_TIGHT = 'grid grid-cols-[7.5rem_1fr] items-start gap-3 py-2';
export const SHEET_DT = 'pt-0.5 text-xs text-muted-foreground';

export function sheetStep(e: KeyboardEvent, open: boolean, onStep?: (dir: 1 | -1) => void): void {
	if (!open || e.metaKey || e.ctrlKey || e.altKey) return;
	const t = e.target as HTMLElement | null;
	if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
	if (e.key === 'ArrowDown' || e.key === 'j') {
		e.preventDefault();
		onStep?.(1);
	} else if (e.key === 'ArrowUp' || e.key === 'k') {
		e.preventDefault();
		onStep?.(-1);
	}
}
