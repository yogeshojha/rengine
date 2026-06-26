export type StatusClass = 'success' | 'info' | 'warning' | 'destructive' | 'muted';

export function httpStatusClass(code: number | null | undefined): StatusClass {
	if (code == null) return 'muted';
	if (code >= 200 && code < 300) return 'success';
	if (code >= 300 && code < 400) return 'info';
	if (code >= 400 && code < 500) return 'warning';
	if (code >= 500) return 'destructive';
	return 'muted';
}

const STATUS_TEXT: Record<StatusClass, string> = {
	success: 'text-success',
	info: 'text-info',
	warning: 'text-warning',
	destructive: 'text-destructive',
	muted: 'text-muted-foreground'
};

export function httpStatusTextClass(code: number | null | undefined): string {
	return STATUS_TEXT[httpStatusClass(code)];
}

export const SENSITIVE_PORTS = new Set([
	21, 22, 23, 25, 53, 135, 139, 445, 1433, 1521, 2049, 2375, 3306, 3389, 5432, 5601, 5900, 6379,
	8086, 9200, 11211, 15672, 27017
]);

export function isSensitivePort(n: number): boolean {
	return SENSITIVE_PORTS.has(n);
}

export function formatBytes(n: number | null | undefined): string {
	if (n == null) return '—';
	if (n < 1024) return `${n} B`;
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
	return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatResponseTime(seconds: number | null | undefined): string {
	if (seconds == null) return '—';
	if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
	return `${seconds.toFixed(2)}s`;
}
