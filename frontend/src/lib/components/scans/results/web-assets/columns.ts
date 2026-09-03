export interface ColumnDef {
	key: string;
	label: string;
}

export interface WebAssetColumn extends ColumnDef {
	sort?: string;
	align?: 'right';
	width: string;
}

export const WEB_ASSET_COLUMNS: WebAssetColumn[] = [
	{ key: 'tech', label: 'Tech', width: 'w-52' },
	{ key: 'ip', label: 'IP / Network', sort: 'ip', width: 'w-32' },
	{ key: 'ports', label: 'Ports', width: 'w-32' },
	{ key: 'sources', label: 'Sources', width: 'w-32' },
	{ key: 'discovered', label: 'Found', sort: 'discovered', width: 'w-24' },
	{ key: 'size', label: 'Size', sort: 'size', align: 'right', width: 'w-16' },
	{ key: 'time', label: 'Time', sort: 'time', align: 'right', width: 'w-16' },
	{ key: 'screenshot', label: 'Screenshot', width: 'w-24' }
];

export const DEFAULT_VISIBLE_COLUMNS = ['tech', 'ip', 'ports', 'screenshot'];
