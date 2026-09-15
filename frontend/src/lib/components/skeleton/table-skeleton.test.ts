import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import ListHeader from '$lib/components/scans/results/table/list-header.svelte';
import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
import { columnCell, type TableColumn } from '$lib/components/scans/results/table/columns';
import {
	WEB_ASSET_COLUMNS,
	WEB_ASSET_LEAD_COLUMNS
} from '$lib/components/scans/results/web-assets/columns';
import { IP_COLUMNS, IP_LEAD_COLUMNS } from '$lib/components/scans/results/ips/columns';
import {
	SERVICE_COLUMNS,
	SERVICE_LEAD_COLUMNS
} from '$lib/components/scans/results/services/columns';
import {
	VULN_COLUMNS,
	VULN_LEAD_COLUMNS,
	ISSUE_COLUMNS,
	ISSUE_LEAD_COLUMNS
} from '$lib/components/scans/results/vulnerabilities/columns';
import {
	ENDPOINT_COLUMNS,
	ENDPOINT_LEAD_COLUMNS
} from '$lib/components/scans/results/endpoints/columns';
import {
	SOFTWARE_COLUMNS,
	SOFTWARE_LEAD_COLUMNS
} from '$lib/components/scans/results/software/columns';

const TABLES: [string, TableColumn[], TableColumn[]][] = [
	['web assets', WEB_ASSET_LEAD_COLUMNS, WEB_ASSET_COLUMNS],
	['addresses', IP_LEAD_COLUMNS, IP_COLUMNS],
	['services', SERVICE_LEAD_COLUMNS, SERVICE_COLUMNS],
	['findings', VULN_LEAD_COLUMNS, VULN_COLUMNS],
	['weaknesses', ISSUE_LEAD_COLUMNS, ISSUE_COLUMNS],
	['endpoints', ENDPOINT_LEAD_COLUMNS, ENDPOINT_COLUMNS],
	['software', SOFTWARE_LEAD_COLUMNS, SOFTWARE_COLUMNS]
];

function header(lead: TableColumn[], columns: TableColumn[]): string {
	return render(ListHeader, {
		props: { lead, columns, sortKey: '', sortDir: 1, onSort: () => {} }
	}).body;
}

function skeletonHeader(lead: TableColumn[], columns: TableColumn[]): string {
	return render(TableSkeleton, { props: { lead, columns, rows: 0 } }).body;
}

function skeletonRows(lead: TableColumn[], columns: TableColumn[]): string {
	return render(TableSkeleton, { props: { lead, columns, rows: 2, header: false } }).body;
}

describe.each(TABLES)('%s skeleton', (_name, lead, columns) => {
	const real = header(lead, columns);
	const fakeHeader = skeletonHeader(lead, columns);
	const fakeRows = skeletonRows(lead, columns);

	it('lays out its rows with the widths the real header uses', () => {
		for (const col of columns) {
			expect(real).toContain(columnCell(col));
			expect(fakeRows).toContain(columnCell(col));
		}
		for (const col of lead) {
			expect(real).toContain(col.width);
			expect(fakeRows).toContain(col.width);
		}
	});

	it('lays out its header the same way', () => {
		for (const col of columns) expect(fakeHeader).toContain(columnCell(col));
		for (const col of lead) expect(fakeHeader).toContain(col.width);
	});

	it('keeps the pinned actions cell the rows carry', () => {
		expect(fakeRows).toContain('sticky right-0');
	});

	it('puts the second line under the column that grows', () => {
		const wide = lead.find((col) => col.grow === true) ?? lead[0];
		const after = fakeRows.slice(fakeRows.indexOf(wide.width) + wide.width.length);
		const next = lead
			.filter((col) => col !== wide)
			.map((col) => after.indexOf(col.width))
			.filter((i) => i > 0);
		const cell = next.length ? after.slice(0, Math.min(...next)) : after;
		expect(cell).toContain('h-3 w-1/3');
	});
});
