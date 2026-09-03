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

export interface SortOption {
	key: string;
	label: string;
}
