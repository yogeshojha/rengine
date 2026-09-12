import type { TableColumn } from '../table/columns';

export const SOFTWARE_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'cve',
		label: 'CVE',
		sort: 'cve',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-56 sm:flex-none'
	},
	{
		key: 'software',
		label: 'Software',
		sort: 'software',
		width: 'hidden min-w-0 shrink-0 sm:block sm:w-56'
	}
];

export const SOFTWARE_COLUMNS: TableColumn[] = [
	{ key: 'asset', label: 'Asset', sort: 'host', width: 'min-w-56 max-w-[22rem]', grow: true },
	{ key: 'severity', label: 'Severity', sort: 'cvss', width: 'w-28' },
	{ key: 'exploitation', label: 'Exploitation', sort: 'epss', width: 'w-36' },
	{ key: 'confidence', label: 'Confidence', width: 'w-32' },
	{ key: 'seen', label: 'Seen', sort: 'seen', width: 'w-24' }
];

export const DEFAULT_VISIBLE_SOFTWARE_COLUMNS = ['asset', 'severity', 'exploitation', 'confidence'];

export const SOFTWARE_SORTS = [
	{ key: 'rank', label: 'Exploitation rank' },
	{ key: 'cvss', label: 'CVSS' },
	{ key: 'epss', label: 'EPSS' },
	{ key: 'cve', label: 'CVE' },
	{ key: 'software', label: 'Software' },
	{ key: 'host', label: 'Host' },
	{ key: 'seen', label: 'Seen' }
];
