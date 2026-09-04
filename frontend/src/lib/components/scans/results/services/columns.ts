import type { TableColumn } from '../table/columns';

// address, port and software are bounded; hostnames are not, so Hosts takes the free space
export const SERVICE_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'service',
		label: 'Service',
		sort: 'port',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-72 sm:flex-none'
	},
	{
		key: 'software',
		label: 'Software',
		sort: 'product',
		width: 'hidden min-w-0 shrink-0 sm:block sm:w-56'
	}
];

export const SERVICE_COLUMNS: TableColumn[] = [
	{ key: 'hosts', label: 'Hosts', sort: 'hosts', width: 'min-w-56 max-w-[18rem]', grow: true },
	{ key: 'web', label: 'Web', sort: 'status', width: 'w-40' },
	{ key: 'network', label: 'Network', sort: 'asn', width: 'w-44' },
	{ key: 'country', label: 'Country', sort: 'country', width: 'w-20' },
	{ key: 'evidence', label: 'Evidence', width: 'w-28' }
];

export const DEFAULT_VISIBLE_SERVICE_COLUMNS = ['hosts', 'web', 'country'];
