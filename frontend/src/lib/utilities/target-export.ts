import type { Target } from '$lib/types/target';
import { csvCell } from '$lib/utilities/csv';
import { downloadBlob } from '$lib/utilities/download';

export type ExportFormat = 'csv' | 'json';

interface Column {
	header: string;
	value: (t: Target) => string;
}

const COLUMNS: Column[] = [
	{ header: 'target_value', value: (t) => t.target_value },
	{ header: 'display_name', value: (t) => t.display_name ?? '' },
	{ header: 'target_type', value: (t) => t.target_type },
	{ header: 'organizations', value: (t) => t.organizations.map((o) => o.name).join('; ') },
	{ header: 'tags', value: (t) => t.tags.map((tag) => tag.name).join('; ') },
	{ header: 'whois_status', value: (t) => t.whois_status },
	{ header: 'registrar', value: (t) => t.whois?.registrar_name ?? '' },
	{ header: 'registrant', value: (t) => t.whois?.registrant_name ?? '' },
	{ header: 'country', value: (t) => t.whois?.country ?? '' },
	{ header: 'network_cidr', value: (t) => t.whois?.network_cidr ?? '' },
	{ header: 'expiration_date', value: (t) => t.whois?.expiration_date ?? '' },
	{ header: 'dns_status', value: (t) => t.dns_status },
	{ header: 'cdn', value: (t) => (t.dns?.cdn ? t.dns.cdn_name || 'yes' : '') },
	{ header: 'bgp_status', value: (t) => t.bgp_status },
	{ header: 'asn', value: (t) => (t.bgp?.asn != null ? String(t.bgp.asn) : '') },
	{ header: 'prefix', value: (t) => t.bgp?.prefix ?? '' },
	{ header: 'created_at', value: (t) => t.created_at },
	{ header: 'updated_at', value: (t) => t.updated_at }
];

export function targetsToCsv(targets: Target[]): string {
	const header = COLUMNS.map((c) => c.header).join(',');
	const rows = targets.map((t) => COLUMNS.map((c) => csvCell(c.value(t))).join(','));
	return [header, ...rows].join('\r\n');
}

export function targetsToJson(targets: Target[]): string {
	const rows = targets.map((t) => {
		const row: Record<string, string> = {};
		for (const col of COLUMNS) row[col.header] = col.value(t);
		return row;
	});
	return JSON.stringify(rows, null, 2);
}

function timestampSlug(): string {
	const d = new Date();
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
}

export function downloadTargets(targets: Target[], format: ExportFormat): void {
	const isCsv = format === 'csv';
	const content = isCsv ? targetsToCsv(targets) : targetsToJson(targets);
	downloadBlob(
		`targets-${timestampSlug()}.${format}`,
		content,
		isCsv ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8'
	);
}
