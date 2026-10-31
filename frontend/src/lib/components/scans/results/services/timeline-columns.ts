import type { TableColumn } from '../table/columns';
import { AddressSort, PortSort } from '$lib/config/timeline';

export const ADDRESS_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'address',
		label: 'Address',
		sort: AddressSort.ADDRESS,
		width: 'min-w-0 flex-[2] contain-inline-size sm:min-w-64'
	}
];

export const ADDRESS_COLUMNS: TableColumn[] = [
	{ key: 'strip', label: 'Scans', width: 'shrink-0' },
	{ key: 'open', label: 'Open now', sort: AddressSort.OPEN, width: 'w-64 shrink-0' },
	{ key: 'first', label: 'First seen', sort: AddressSort.FIRST_SEEN, width: 'w-24 shrink-0' },
	{
		key: 'changes',
		label: 'Changes',
		sort: AddressSort.CHANGES,
		align: 'right',
		width: 'w-16 shrink-0'
	},
	{ key: 'last', label: 'Last change', sort: AddressSort.LAST_CHANGE, width: 'w-64 shrink-0' }
];

export const PORT_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'port',
		label: 'Port',
		sort: PortSort.PORT,
		width: 'min-w-0 flex-[2] contain-inline-size sm:min-w-56'
	}
];

export const PORT_COLUMNS: TableColumn[] = [
	{ key: 'strip', label: 'Addresses per scan', width: 'shrink-0' },
	{ key: 'now', label: 'Now', sort: PortSort.ADDRESSES, align: 'right', width: 'w-16 shrink-0' },
	{ key: 'first', label: 'First seen', sort: PortSort.FIRST_SEEN, width: 'w-24 shrink-0' },
	{ key: 'last', label: 'Last change', sort: PortSort.LAST_CHANGE, width: 'w-56 shrink-0' }
];

// a matrix cell carries a count
export const MATRIX_CELL_PX = 18;
