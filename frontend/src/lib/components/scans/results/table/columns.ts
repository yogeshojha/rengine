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
	// contain-inline-size: a growing column fills the row but never widens it past the card
	const grow = col.grow
		? `flex-1 contain-inline-size ${/(^|\s)min-w-/.test(col.width) ? '' : 'min-w-0'}`
		: 'shrink-0';
	return `hidden sm:flex ${grow} ${col.width} ${col.align === 'right' ? 'justify-end' : ''}`;
}

// row chrome around the columns, in px: px-4 padding, checkbox + gap, pinned actions (sm:w-[5.75rem])
const ROW_PAD_PX = 32;
const SELECT_PX = 16 + 12;
const ACTIONS_PX = 92;
const GAP_PX = 12;

function sizePx(token: string): number {
	const m = token.match(/^(?:min-)?w-(?:\[(\d+(?:\.\d+)?)(px|rem)\]|(\d+(?:\.\d+)?))$/);
	if (!m) return 0;
	if (m[3]) return Number(m[3]) * 4;
	return m[2] === 'rem' ? Number(m[1]) * 16 : Number(m[1]);
}

/** The narrowest a column gets at desktop widths: its `w-*` / `min-w-*`, `sm:` winning. */
export function columnPx(col: TableColumn): number {
	const size: Record<'w' | 'min', number> = { w: 0, min: 0 };
	const desktop = new Set<string>();
	for (const raw of col.width.split(/\s+/)) {
		const sm = raw.startsWith('sm:');
		const token = sm ? raw.slice(3) : raw;
		const prop = token.startsWith('min-w-') ? 'min' : token.startsWith('w-') ? 'w' : null;
		if (!prop || (!sm && desktop.has(prop))) continue;
		if (sm) desktop.add(prop);
		size[prop] = sizePx(token);
	}
	return Math.max(size.w, size.min);
}

/**
 * The chosen columns that fit beside the lead columns in `width` px, in order; the rest fold
 * away until there is room, like the targets list. 0 means not measured yet, so keep them all.
 */
export function fitColumns(
	columns: TableColumn[],
	width: number,
	lead: TableColumn[],
	selectable = true
): TableColumn[] {
	if (!width) return columns;
	let room =
		width -
		ROW_PAD_PX -
		ACTIONS_PX -
		(selectable ? SELECT_PX : 0) -
		lead.reduce((n, col) => n + columnPx(col) + GAP_PX, 0);
	const fitted: TableColumn[] = [];
	for (const col of columns) {
		const need = columnPx(col) + GAP_PX;
		if (need > room) break;
		room -= need;
		fitted.push(col);
	}
	return fitted;
}

/** Calls back with an element's content width as it resizes. */
export function trackWidth(set: (width: number) => void) {
	return (node: HTMLElement) => {
		const observer = new ResizeObserver(([entry]) => set(Math.floor(entry.contentRect.width)));
		observer.observe(node);
		return () => observer.disconnect();
	};
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
