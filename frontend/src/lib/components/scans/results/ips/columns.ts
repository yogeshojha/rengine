import type { TableColumn } from '../table/columns';

export const IP_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'ip',
		label: 'Address',
		sort: 'ip',
		width: 'min-w-0 flex-[3] contain-inline-size sm:min-w-56'
	},
	{
		key: 'network',
		label: 'Network',
		sort: 'asn',
		width: 'hidden min-w-40 flex-[2] sm:block'
	}
];

export const IP_COLUMNS: TableColumn[] = [
	{ key: 'ports', label: 'Ports', sort: 'ports', width: 'w-44' },
	{ key: 'hosts', label: 'Hosts', sort: 'hosts', width: 'w-56' },
	{ key: 'country', label: 'Country', sort: 'country', width: 'w-20' },
	{ key: 'prefix', label: 'Prefix', width: 'w-36' },
	{ key: 'ptr', label: 'PTR', width: 'w-48' },
	{ key: 'assets', label: 'Web', sort: 'assets', align: 'right', width: 'w-16' }
];

export const DEFAULT_VISIBLE_IP_COLUMNS = ['ports', 'hosts', 'country'];
