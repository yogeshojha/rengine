import type { TableColumn } from '../table/columns';

export const VULN_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'finding',
		label: 'Finding',
		sort: 'risk',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-[22rem] sm:flex-none'
	},
	{
		key: 'location',
		label: 'Location',
		sort: 'host',
		width: 'hidden min-w-0 shrink-0 sm:flex sm:w-72'
	}
];

export const ISSUE_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'issue',
		label: 'Weakness',
		sort: 'risk',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-[23rem] sm:flex-none'
	}
];

export const ISSUE_COLUMNS: TableColumn[] = [
	{ key: 'affected', label: 'Affected', sort: 'host', width: 'min-w-52 max-w-[22rem]', grow: true },
	{ key: 'risk', label: 'Risk', sort: 'cvss', width: 'w-36' },
	{ key: 'review', label: 'Review', width: 'w-28' },
	{ key: 'seen', label: 'First seen', sort: 'seen', width: 'w-24' }
];
