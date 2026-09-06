import type { IconComponent } from '$lib/config/icons';
import FileTextIcon from '@lucide/svelte/icons/file-text';
import FileCodeIcon from '@lucide/svelte/icons/file-code';
import FileJsonIcon from '@lucide/svelte/icons/file-json';
import FileTypeIcon from '@lucide/svelte/icons/file-type';

export const ReportStatus = {
	QUEUED: 'queued',
	RUNNING: 'running',
	COMPLETED: 'completed',
	FAILED: 'failed'
} as const;
export type ReportStatusValue = (typeof ReportStatus)[keyof typeof ReportStatus];

export const REPORT_STATUS_LABELS: Record<string, string> = {
	queued: 'Queued',
	running: 'Generating',
	completed: 'Ready',
	failed: 'Failed'
};

export const REPORT_STATUS_TONE: Record<string, string> = {
	queued: 'text-muted-foreground',
	running: 'text-info',
	completed: 'text-success',
	failed: 'text-destructive'
};

export const ReportFormat = {
	PDF: 'pdf',
	HTML: 'html',
	MARKDOWN: 'markdown',
	JSON: 'json'
} as const;
export type ReportFormatValue = (typeof ReportFormat)[keyof typeof ReportFormat];

export const FORMAT_ICONS: Record<string, IconComponent> = {
	pdf: FileTextIcon,
	html: FileCodeIcon,
	markdown: FileTypeIcon,
	json: FileJsonIcon
};

export const FORMAT_LABELS: Record<string, string> = {
	pdf: 'PDF',
	html: 'HTML',
	markdown: 'Markdown',
	json: 'JSON'
};

export const ReportScope = {
	SCAN: 'scan',
	TARGET: 'target'
} as const;

export const SECTION_GROUP_ORDER = [
	'front_matter',
	'summary',
	'findings',
	'surface',
	'intelligence',
	'appendix'
] as const;

export const TERMINAL_STATUSES = new Set<string>([ReportStatus.COMPLETED, ReportStatus.FAILED]);

export function isLive(status: string): boolean {
	return !TERMINAL_STATUSES.has(status);
}

export function formatBytes(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
