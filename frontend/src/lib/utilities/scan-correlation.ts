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

export const STATUS_DOT: Record<StatusClass, string> = {
	success: 'bg-success',
	info: 'bg-info',
	warning: 'bg-warning',
	destructive: 'bg-destructive',
	muted: 'bg-muted-foreground/40'
};

const CLASS_LABEL: Record<StatusClass, string> = {
	success: 'Success',
	info: 'Redirect',
	warning: 'Client error',
	destructive: 'Server error',
	muted: 'No HTTP response'
};

const STATUS_REASON: Record<number, string> = {
	200: 'OK',
	201: 'Created',
	204: 'No Content',
	301: 'Moved Permanently',
	302: 'Found',
	303: 'See Other',
	307: 'Temporary Redirect',
	308: 'Permanent Redirect',
	400: 'Bad Request',
	401: 'Unauthorized',
	403: 'Forbidden',
	404: 'Not Found',
	405: 'Method Not Allowed',
	408: 'Request Timeout',
	429: 'Too Many Requests',
	500: 'Internal Server Error',
	502: 'Bad Gateway',
	503: 'Service Unavailable',
	504: 'Gateway Timeout'
};

export function httpStatusReason(code: number | null | undefined): string {
	if (code == null) return CLASS_LABEL.muted;
	return STATUS_REASON[code] ?? CLASS_LABEL[httpStatusClass(code)];
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

const PRIVATE_V4 = [
	/^10\./,
	/^172\.(1[6-9]|2\d|3[01])\./,
	/^192\.168\./,
	/^127\./,
	/^169\.254\./,
	/^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./
];

export function isPrivateIp(ip: string): boolean {
	if (ip.includes(':')) return /^(fc|fd|fe80|::1$)/i.test(ip);
	return PRIVATE_V4.some((re) => re.test(ip));
}
