const LAYER = '[role=dialog], [role=alertdialog]';
const OPEN_LAYER = '[role=dialog][data-state=open], [role=alertdialog][data-state=open]';
const FIELD = 'input, textarea, select, .cm-editor';
const LIST = '[role=menu], [role=listbox], [role=combobox]';

/** The open dialog, sheet or confirm drawn above the others. */
export function topLayer(): Element | null {
	if (typeof document === 'undefined') return null;
	const open = document.querySelectorAll(OPEN_LAYER);
	return open[open.length - 1] ?? null;
}

/** True when an open layer sits above the one holding the element. */
export function underLayer(el: Element | null): boolean {
	return topLayer() !== (el?.closest(LAYER) ?? null);
}

/** True when a key press belongs to a text field, a menu or a list. */
export function keyTaken(target: EventTarget | null): boolean {
	if (!(target instanceof Element)) return false;
	if (target instanceof HTMLElement && target.isContentEditable) return true;
	return target.closest(`${FIELD}, ${LIST}`) !== null;
}
