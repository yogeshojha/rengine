import type { TableColumn } from '../table/columns';

// an address and its network are bounded strings; hostnames are the variable
// content, so Hosts takes the free space instead of Address hogging it
export const IP_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'ip',
		label: 'Address',
		sort: 'ip',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-72 sm:flex-none'
	},
	{
		key: 'network',
		label: 'Network',
		sort: 'asn',
		width: 'hidden min-w-0 shrink-0 sm:block sm:w-60'
	}
];

export const IP_COLUMNS: TableColumn[] = [
	// capped so the default column set still fits a ~1240px content area without
	// horizontal scroll; the row sizes to content inside the ScrollArea, so an
	// uncapped flex-1 pushes Country off screen
	{ key: 'hosts', label: 'Hosts', sort: 'hosts', width: 'min-w-56 max-w-[29rem]', grow: true },
	{ key: 'ports', label: 'Ports', sort: 'ports', width: 'w-44' },
	{ key: 'country', label: 'Country', sort: 'country', width: 'w-20' },
	{ key: 'prefix', label: 'Prefix', width: 'w-36' },
	{ key: 'ptr', label: 'PTR', width: 'w-48' },
	{ key: 'assets', label: 'Web', sort: 'assets', align: 'right', width: 'w-16' }
];

export const DEFAULT_VISIBLE_IP_COLUMNS = ['hosts', 'ports', 'country'];
