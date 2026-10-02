const SHEET_STEP_KEYS = new Set(['ArrowUp', 'ArrowDown', 'j', 'k']);

/** Keeps a key pressed in a notes layer from stepping the sheet beneath it. */
export function holdSheetKeys(e: KeyboardEvent): void {
	if (SHEET_STEP_KEYS.has(e.key)) e.stopPropagation();
}
