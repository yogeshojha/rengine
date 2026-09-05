import type { TableColumn } from '$lib/components/scans/results/table/columns';

export const ASSET_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'name',
		label: 'Host',
		sort: 'name',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-80 sm:flex-none'
	},
	{ key: 'status', label: 'Status', sort: 'status', width: 'w-12 shrink-0 sm:w-16' }
];

export const ASSET_COLUMNS: TableColumn[] = [
	{ key: 'title', label: 'Title', width: 'min-w-40 max-w-[22rem]', grow: true },
	{ key: 'tech', label: 'Tech', width: 'w-28' },
	{ key: 'ip', label: 'Address', width: 'w-36' },
	{ key: 'sources', label: 'Sources', width: 'w-28' },
	{ key: 'scans', label: 'Scans', sort: 'scans', align: 'right', width: 'w-16' },
	{ key: 'first_seen', label: 'First seen', sort: 'first_seen', align: 'right', width: 'w-24' },
	{ key: 'last_seen', label: 'Last seen', sort: 'last_seen', align: 'right', width: 'w-24' }
];

export const DEFAULT_ASSET_COLUMNS = ['title', 'tech', 'ip', 'scans', 'first_seen', 'last_seen'];
