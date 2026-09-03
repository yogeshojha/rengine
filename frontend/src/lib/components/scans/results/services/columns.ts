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
		width: 'hidden min-w-0 shrink-0 sm:block sm:w-44'
	}
];

export const SERVICE_COLUMNS: TableColumn[] = [
	// capped so the default set fits a ~1180px content area; the row is laid out at max-content
	{ key: 'hosts', label: 'Hosts', sort: 'hosts', width: 'min-w-60 max-w-[22rem]', grow: true },
	{ key: 'web', label: 'Web', sort: 'status', width: 'w-48' },
	{ key: 'network', label: 'Network', sort: 'asn', width: 'w-44' },
	{ key: 'country', label: 'Country', sort: 'country', width: 'w-20' },
	{ key: 'evidence', label: 'Evidence', width: 'w-28' }
];

export const DEFAULT_VISIBLE_SERVICE_COLUMNS = ['hosts', 'web', 'country'];
