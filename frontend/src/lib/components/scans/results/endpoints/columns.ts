import type { TableColumn } from '../table/columns';

// the identity block: status rail, then the path itself, which takes the free space
export const ENDPOINT_LEAD_COLUMNS: TableColumn[] = [
	{ key: 'status', label: 'Status', width: 'w-[4.5rem]', sort: 'status' },
	{ key: 'path', label: 'Path', width: 'min-w-64 max-w-[30rem]', grow: true, sort: 'path' }
];

export const ENDPOINT_COLUMNS: TableColumn[] = [
	{ key: 'host', label: 'Host', width: 'w-[13rem]', sort: 'host' },
	{ key: 'kind', label: 'Kind', width: 'w-[6.5rem]', sort: 'class' },
	{ key: 'params', label: 'Parameters', width: 'w-[11rem]', sort: 'params' },
	{ key: 'title', label: 'Title', width: 'w-[14rem]' },
	{ key: 'tech', label: 'Technology', width: 'w-[11rem]' },
	{ key: 'size', label: 'Size', width: 'w-[5.5rem]', align: 'right', sort: 'length' },
	{ key: 'sources', label: 'Found by', width: 'w-[8rem]' },
	{ key: 'seen', label: 'First seen', width: 'w-[7rem]', sort: 'seen' }
];

// title is off by default: the path and its badges already carry the meaning, and the
// tree view's pane is narrower than the full-width list
export const DEFAULT_VISIBLE_ENDPOINT_COLUMNS = ['host', 'kind', 'params', 'size', 'sources'];
