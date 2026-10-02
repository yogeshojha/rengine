import type { IconComponent } from '$lib/config/icons';
import FileTextIcon from '@lucide/svelte/icons/file-text';
import FileCodeIcon from '@lucide/svelte/icons/file-code';
import FileJsonIcon from '@lucide/svelte/icons/file-json';
import FileTypeIcon from '@lucide/svelte/icons/file-type';

export const ReportStatus = {
	QUEUED: 'queued',
	RUNNING: 'running',
	COMPLETED: 'completed',
	FAILED: 'failed',
	EXPIRED: 'expired'
} as const;
export type ReportStatusValue = (typeof ReportStatus)[keyof typeof ReportStatus];

export const REPORT_STATUS_LABELS: Record<ReportStatusValue, string> = {
	queued: 'Queued',
	running: 'Generating',
	completed: 'Ready',
	failed: 'Failed',
	expired: 'Expired'
};

export const REPORT_STATUS_TONE: Record<ReportStatusValue, string> = {
	queued: 'text-muted-foreground',
	running: 'text-info',
	completed: 'text-success',
	failed: 'text-destructive',
	expired: 'text-muted-foreground'
};

export const ReportFormat = {
	PDF: 'pdf',
	HTML: 'html',
	MARKDOWN: 'markdown',
	JSON: 'json'
} as const;

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

export const TERMINAL_STATUSES = new Set<string>([
	ReportStatus.COMPLETED,
	ReportStatus.FAILED,
	ReportStatus.EXPIRED
]);

export function isLive(status: string): boolean {
	return !TERMINAL_STATUSES.has(status);
}

/** Mirrors shared/definitions/reports.py:MAX_LOGO_BYTES */
export const MAX_EMBEDDED_IMAGE = 512_000;
export const MAX_EMBEDDED_IMAGE_KB = Math.floor((MAX_EMBEDDED_IMAGE * 3) / 4 / 1024);

export async function readEmbeddedImage(file: File): Promise<string | null> {
	const dataUrl = await new Promise<string>((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(String(reader.result));
		reader.onerror = reject;
		reader.readAsDataURL(file);
	});
	return dataUrl.length > MAX_EMBEDDED_IMAGE ? null : dataUrl;
}

export function catalogLabel(
	list: { key: string; label: string }[] | undefined,
	key: string
): string {
	return list?.find((i) => i.key === key)?.label ?? key;
}

export const FONT_ROLE_STACKS: Record<string, string> = {
	sans: 'ui-sans-serif, system-ui, sans-serif',
	serif: 'Georgia, "Times New Roman", serif',
	mono: 'ui-monospace, SFMono-Regular, Menlo, monospace'
};

/** Browser fallback stack for a report face. */
export function fontStack(slug: string, fonts: { slug: string; name: string; role: string }[]) {
	const font = fonts.find((f) => f.slug === slug);
	const fallback = FONT_ROLE_STACKS[font?.role ?? 'sans'] ?? FONT_ROLE_STACKS.sans;
	return font ? `"${font.name}", ${fallback}` : fallback;
}

export const LibraryOrigin = {
	BUILTIN: 'builtin',
	CUSTOM: 'custom'
} as const;

export const LibraryTab = {
	ALL: 'all',
	DEFAULT: 'default',
	CUSTOM: 'custom'
} as const;
export type LibraryTabValue = (typeof LibraryTab)[keyof typeof LibraryTab];

export const LIBRARY_TABS = [
	{ key: LibraryTab.ALL, label: 'All' },
	{ key: LibraryTab.DEFAULT, label: 'Default' },
	{ key: LibraryTab.CUSTOM, label: 'Custom' }
];

export function libraryCounts(builtin: boolean[]): Record<LibraryTabValue, number> {
	const n = builtin.filter(Boolean).length;
	return { all: builtin.length, default: n, custom: builtin.length - n };
}

export function inLibraryTab(tab: string, builtin: boolean): boolean {
	return tab === LibraryTab.ALL || builtin === (tab === LibraryTab.DEFAULT);
}

export const SectionRole = {
	CONTENT: 'content',
	FURNITURE: 'furniture'
} as const;
