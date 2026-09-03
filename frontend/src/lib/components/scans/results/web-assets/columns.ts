import type { TableColumn } from '../table/columns';

export const WEB_ASSET_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'name',
		label: 'Host',
		sort: 'name',
		width: 'min-w-0 flex-[3] contain-inline-size sm:min-w-56'
	},
	{ key: 'status', label: 'Status', sort: 'status', width: 'w-12 shrink-0 sm:w-16' },
	{ key: 'title', label: 'Title', sort: 'title', width: 'hidden min-w-40 flex-[2] sm:block' }
];

export const WEB_ASSET_COLUMNS: TableColumn[] = [
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
