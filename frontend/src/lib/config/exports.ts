/** Mirrors shared/definitions/exports.py */

export const ExportFormat = {
	CSV: 'csv',
	JSON: 'json',
	TXT: 'txt'
} as const;

export type ExportFormatValue = (typeof ExportFormat)[keyof typeof ExportFormat];

export const EXPORT_FORMATS: ExportFormatValue[] = [
	ExportFormat.CSV,
	ExportFormat.TXT,
	ExportFormat.JSON
];

export const FORMAT_LABELS: Record<string, string> = {
	[ExportFormat.CSV]: 'CSV',
	[ExportFormat.JSON]: 'JSON',
	[ExportFormat.TXT]: 'Text'
};

export const ExportStatus = {
	QUEUED: 'queued',
	RUNNING: 'running',
	COMPLETED: 'completed',
	FAILED: 'failed',
	EXPIRED: 'expired'
} as const;

export type ExportStatusValue = (typeof ExportStatus)[keyof typeof ExportStatus];

export const EXPORT_STATUS_LABELS: Record<string, string> = {
	[ExportStatus.QUEUED]: 'Queued',
	[ExportStatus.RUNNING]: 'Preparing',
	[ExportStatus.COMPLETED]: 'Ready',
	[ExportStatus.FAILED]: 'Failed',
	[ExportStatus.EXPIRED]: 'Expired'
};

export const EXPORT_STATUS_TONE: Record<string, string> = {
	[ExportStatus.QUEUED]: 'text-muted-foreground',
	[ExportStatus.RUNNING]: 'text-info',
	[ExportStatus.COMPLETED]: 'text-success',
	[ExportStatus.FAILED]: 'text-destructive',
	[ExportStatus.EXPIRED]: 'text-muted-foreground'
};

export const BUNDLE = 'bundle';

const LIVE: string[] = [ExportStatus.QUEUED, ExportStatus.RUNNING];

export function isLive(status: string): boolean {
	return LIVE.includes(status);
}

export function formatBytes(bytes: number): string {
	if (!bytes) return '';
	const units = ['B', 'KB', 'MB', 'GB'];
	let value = bytes;
	let unit = 0;
	while (value >= 1024 && unit < units.length - 1) {
		value /= 1024;
		unit += 1;
	}
	return `${value < 10 && unit > 0 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}
