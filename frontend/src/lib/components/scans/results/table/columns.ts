export interface TableColumn {
	key: string;
	label: string;
	sort?: string;
	align?: 'right';
	width: string;
	grow?: boolean;
}

export const TARGET_COLUMN: TableColumn = {
	key: 'target',
	label: 'Target',
	width: 'w-40'
};

export function withTarget(columns: TableColumn[], projectWide: boolean): TableColumn[] {
	return projectWide ? [TARGET_COLUMN, ...columns] : columns;
}

export interface SortOption {
	key: string;
	label: string;
}

/** Hover-revealed row control; always visible on touch (no hover) and on keyboard focus. */
export const REVEAL =
	'opacity-0 group-hover:opacity-100 focus-visible:opacity-100 pointer-coarse:opacity-100';
/** Like REVEAL, but only hidden from the sm breakpoint up. */
export const REVEAL_SM =
	'sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100 pointer-coarse:opacity-100';

export const ACTIONS_PIN = 'sticky right-0 z-10 ml-auto shrink-0 self-stretch bg-card';
export const ACTIONS_BODY =
	'flex h-full w-8 items-center justify-end gap-0.5 transition-colors sm:w-[5.75rem]';

export function rowTone(active: boolean, focused: boolean): string {
	if (active) return 'bg-primary/5 hover:bg-primary/10';
	return focused ? 'bg-muted/40 shadow-[inset_2px_0_0_0_var(--primary)]' : 'hover:bg-muted/30';
}

export function columnCell(col: TableColumn): string {
	const grow = col.grow ? 'min-w-0 flex-1' : 'shrink-0';
	return `hidden sm:flex ${grow} ${col.width} ${col.align === 'right' ? 'justify-end' : ''}`;
}

export function selectAllState(checked: number, total: number): boolean | 'indeterminate' {
	if (total > 0 && checked === total) return true;
	return checked > 0 ? 'indeterminate' : false;
}

export function pinTone(active: boolean, focused: boolean): string {
	if (active) return 'bg-primary/5 group-hover:bg-primary/10';
	return focused ? 'bg-muted/40' : 'group-hover:bg-muted/30';
}

const CONTROL =
	'a, button, [role=button], [role=checkbox], [role=switch], [role=radio], [role=tab], [role=menuitem]';

export function inPopover(target: EventTarget | null): boolean {
	return target instanceof Element && target.closest('[data-slot="popover-content"]') !== null;
}

export function onControl(target: EventTarget | null, row: string): boolean {
	const control = target instanceof Element ? target.closest(CONTROL) : null;
	return !!control && !control.matches(row);
}

const ROW_PAD: Record<string, string> = { compact: 'py-2', cozy: 'py-3' };

export function rowPadding(density: string): string {
	return ROW_PAD[density] ?? ROW_PAD.cozy;
}

export function readPref<T>(key: string, fallback: T): T {
	try {
		const raw = localStorage.getItem(key);
		return raw ? (JSON.parse(raw) as T) : fallback;
	} catch {
		return fallback;
	}
}

export function writePref(key: string, value: unknown) {
	try {
		localStorage.setItem(key, JSON.stringify(value));
	} catch {}
}
