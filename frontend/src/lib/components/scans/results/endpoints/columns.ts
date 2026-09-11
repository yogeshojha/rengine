import type { TableColumn } from '../table/columns';

export const ENDPOINT_LEAD_COLUMNS: TableColumn[] = [
	{ key: 'status', label: 'Status', width: 'w-[5.5rem]', sort: 'status' },
	{ key: 'path', label: 'Path', width: 'min-w-64 max-w-[30rem]', grow: true, sort: 'path' }
];

export const OUTLINE_LEAD_COLUMNS: TableColumn[] = [
	{ key: 'path', label: 'Path', width: 'min-w-80 max-w-[44rem]', grow: true, sort: 'path' },
	{ key: 'status', label: 'Status', width: 'w-[5.5rem]', sort: 'status' }
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

export const OUTLINE_HIDDEN_COLUMNS: ReadonlySet<string> = new Set(['host']);

export const DEFAULT_VISIBLE_ENDPOINT_COLUMNS = ['host', 'kind', 'params', 'size', 'sources'];
export const DEFAULT_VISIBLE_OUTLINE_COLUMNS = ['params', 'size', 'sources'];

export const HOST_LEAD_COLUMNS: TableColumn[] = [
	{ key: 'host', label: 'Host', width: 'min-w-80 max-w-[40rem]', grow: true, sort: 'host' },
	{ key: 'endpoints', label: 'Endpoints', width: 'w-[8.5rem]', align: 'right', sort: 'endpoints' }
];

export const HOST_COLUMNS: TableColumn[] = [
	{ key: 'input', label: 'Input', width: 'w-[4.5rem]', align: 'right', sort: 'input' },
	{ key: 'api', label: 'API', width: 'w-[3.5rem]', align: 'right', sort: 'api' },
	{ key: 'why', label: 'Why', width: 'w-[13rem]' },
	{ key: 'new', label: 'New', width: 'w-[4rem]', align: 'right', sort: 'new' },
	{ key: 'sources', label: 'Found by', width: 'w-[7rem]' }
];
