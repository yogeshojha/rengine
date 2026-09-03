export interface ColumnDef {
	key: string;
	label: string;
}

export interface TableColumn extends ColumnDef {
	sort?: string;
	align?: 'right';
	width: string;
}

export interface SortOption {
	key: string;
	label: string;
}
