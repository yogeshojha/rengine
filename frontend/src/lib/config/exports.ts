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
export const BUNDLE_LABEL = 'All dimensions';

const LIVE: string[] = [ExportStatus.QUEUED, ExportStatus.RUNNING];

export function isLive(status: string): boolean {
	return LIVE.includes(status);
}
