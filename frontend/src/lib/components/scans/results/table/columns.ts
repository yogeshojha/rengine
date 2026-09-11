export interface ColumnDef {
	key: string;
	label: string;
}

export interface TableColumn extends ColumnDef {
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

export const ACTIONS_PIN = 'sticky right-0 z-10 ml-auto shrink-0 self-stretch bg-card';
export const ACTIONS_BODY =
	'flex h-full w-8 items-center justify-end gap-0.5 transition-colors sm:w-[3.75rem]';

export function rowTone(active: boolean, focused: boolean): string {
	if (active) return 'bg-primary/5 hover:bg-primary/10';
	return focused ? 'bg-muted/40 shadow-[inset_2px_0_0_0_var(--primary)]' : 'hover:bg-muted/30';
}

export function pinTone(active: boolean, focused: boolean): string {
	if (active) return 'bg-primary/5 group-hover:bg-primary/10';
	return focused ? 'bg-muted/40' : 'group-hover:bg-muted/30';
}
