import type { ScanExportRow } from '$lib/types/scan';

export type ExportFormat = 'csv' | 'json';

interface Column {
	header: string;
	value: (s: ScanExportRow) => string;
}

const COLUMNS: Column[] = [
	{ header: 'target', value: (s) => s.target },
	{ header: 'status', value: (s) => s.status },
	{ header: 'engine', value: (s) => s.engine },
	{ header: 'context', value: (s) => s.context ?? '' },
	{ header: 'subdomains', value: (s) => String(s.subdomains) },
	{ header: 'ips', value: (s) => String(s.ips) },
	{ header: 'open_ports', value: (s) => String(s.open_ports) },
	{ header: 'vulnerabilities', value: (s) => String(s.vulnerabilities) },
	{ header: 'endpoints', value: (s) => String(s.endpoints) },
	{
		header: 'duration_seconds',
		value: (s) => (s.duration_seconds != null ? String(s.duration_seconds) : '')
	},
	{ header: 'started_at', value: (s) => s.started_at ?? '' },
	{ header: 'completed_at', value: (s) => s.completed_at ?? '' },
	{ header: 'created_at', value: (s) => s.created_at }
];

function escapeCsv(value: string): string {
	if (/[",\n\r]/.test(value)) {
		return `"${value.replace(/"/g, '""')}"`;
	}
	return value;
}

export function scansToCsv(scans: ScanExportRow[]): string {
	const header = COLUMNS.map((c) => c.header).join(',');
	const rows = scans.map((s) => COLUMNS.map((c) => escapeCsv(c.value(s))).join(','));
	return [header, ...rows].join('\r\n');
}

export function scansToJson(scans: ScanExportRow[]): string {
	return JSON.stringify(scans, null, 2);
}

function timestampSlug(): string {
	const d = new Date();
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
}

export function downloadScans(scans: ScanExportRow[], format: ExportFormat): void {
	const isCsv = format === 'csv';
	const content = isCsv ? scansToCsv(scans) : scansToJson(scans);
	const blob = new Blob([content], {
		type: isCsv ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8'
	});
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = `scans-${timestampSlug()}.${format}`;
	document.body.appendChild(link);
	link.click();
	link.remove();
	URL.revokeObjectURL(url);
}
