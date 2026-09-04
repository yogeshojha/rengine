import type { TableColumn } from '../table/columns';

// severity and the finding name lead; the exact location is the second fixed lead
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
		width: 'hidden min-w-0 shrink-0 sm:block sm:w-72'
	}
];

export const VULN_COLUMNS: TableColumn[] = [
	{ key: 'asset', label: 'Asset', width: 'min-w-56 max-w-[20rem]', grow: true },
	{ key: 'risk', label: 'Risk', sort: 'cvss', width: 'w-40' },
	{ key: 'reach', label: 'Reach', width: 'w-24' },
	{ key: 'type', label: 'Type', sort: 'type', width: 'w-24' },
	{ key: 'scanner', label: 'Scanner', width: 'w-28' },
	{ key: 'review', label: 'Review', width: 'w-28' },
	{ key: 'seen', label: 'First seen', sort: 'seen', width: 'w-28' }
];

export const DEFAULT_VISIBLE_VULN_COLUMNS = ['asset', 'risk', 'reach', 'review'];

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
