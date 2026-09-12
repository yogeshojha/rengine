import type { TableColumn } from '../scans/results/table/columns';
import type { SortOption } from '../scans/results/table/columns';
import { EVIDENCE_LABELS, EVIDENCE_ORDER } from '$lib/config/evidence';

export const CVE_LEAD_COLUMNS: TableColumn[] = [
	{
		key: 'cve',
		label: 'CVE',
		sort: 'cve',
		width: 'min-w-0 flex-1 contain-inline-size sm:w-56 sm:flex-none'
	},
	{
		key: 'severity',
		label: 'Severity',
		sort: 'severity',
		width: 'hidden shrink-0 sm:block sm:w-32'
	}
];

export const CVE_COLUMNS: TableColumn[] = [
	{ key: 'epss', label: 'EPSS', sort: 'epss', width: 'w-20', align: 'right' },
	{ key: 'assets', label: 'Assets', sort: 'assets', width: 'w-20', align: 'right' },
	{ key: 'targets', label: 'Targets', sort: 'targets', width: 'w-20', align: 'right' },
	{ key: 'evidence', label: 'Evidence', width: 'min-w-0 w-56', grow: true },
	{ key: 'first_seen', label: 'First seen', sort: 'first_seen', width: 'w-28' }
];

export const CVE_SORTS: SortOption[] = [
	{ key: 'rank', label: 'Exploitation rank' },
	{ key: 'severity', label: 'Severity' },
	{ key: 'cvss', label: 'CVSS' },
	{ key: 'epss', label: 'EPSS' },
	{ key: 'assets', label: 'Assets' },
	{ key: 'targets', label: 'Targets' },
	{ key: 'first_seen', label: 'First seen' },
	{ key: 'cve', label: 'Identifier' }
];

export interface CveFilter {
	key: string;
	label: string;
}

export const CVE_FILTERS: CveFilter[] = [
	{ key: 'kev', label: 'Known exploited' },
	{ key: 'ransomware', label: 'Ransomware' },
	...EVIDENCE_ORDER.map((rung) => ({ key: rung, label: EVIDENCE_LABELS[rung] }))
];
