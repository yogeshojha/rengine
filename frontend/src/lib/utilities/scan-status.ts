import {
	Clock,
	LoaderCircle,
	CircleCheck,
	CircleX,
	CircleMinus,
	TriangleAlert,
	Ban,
	Network,
	Server,
	Plug,
	Bug,
	Link2
} from 'lucide-svelte';
import type { ScanActivityStatus, ScanRead, ScanStatus, ScanSortKey } from '$lib/types/scan';

type IconComponent = typeof Network;

export const SCAN_STATUS_LABEL: Record<ScanStatus, string> = {
	pending: 'Queued',
	running: 'Running',
	completed: 'Completed',
	failed: 'Failed',
	cancelled: 'Cancelled'
};

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive';

export function scanStatusVariant(s: ScanStatus): BadgeVariant {
	if (s === 'failed' || s === 'cancelled') return 'destructive';
	if (s === 'completed') return 'default';
	return 'secondary';
}

export function scanStatusIcon(s: ScanStatus): IconComponent {
	switch (s) {
		case 'running':
			return LoaderCircle;
		case 'pending':
			return Clock;
		case 'completed':
			return CircleCheck;
		case 'cancelled':
			return Ban;
		default:
			return TriangleAlert;
	}
}

export function isLiveStatus(s: ScanStatus): boolean {
	return s === 'running' || s === 'pending';
}

export function activityStatusIcon(s: ScanActivityStatus): IconComponent {
	switch (s) {
		case 'running':
			return LoaderCircle;
		case 'pending':
			return Clock;
		case 'success':
			return CircleCheck;
		case 'failed':
			return CircleX;
		case 'aborted':
			return Ban;
		default:
			return CircleMinus;
	}
}

export function activityStatusClass(s: ScanActivityStatus): string {
	switch (s) {
		case 'failed':
			return 'text-destructive';
		case 'aborted':
		case 'skipped':
			return 'text-amber-600 dark:text-amber-500';
		case 'running':
			return 'text-foreground';
		default:
			return 'text-muted-foreground';
	}
}

export const ACTIVITY_STATUS_LABEL: Record<ScanActivityStatus, string> = {
	pending: 'Queued',
	running: 'Running',
	success: 'Success',
	failed: 'Failed',
	skipped: 'Skipped',
	aborted: 'Aborted'
};

export const SCAN_POLL_MS = 4000;

export const SCAN_STATUS_RANK: Record<ScanStatus, number> = {
	running: 0,
	pending: 1,
	completed: 2,
	failed: 3,
	cancelled: 4
};

export function elapsedSeconds(scan: ScanRead, now: number = Date.now()): number | null {
	if (!isLiveStatus(scan.status) || !scan.started_at) return null;
	return Math.max(0, (now - new Date(scan.started_at).getTime()) / 1000);
}

export function formatSeconds(total: number): string {
	const t = Math.round(total);
	if (t < 60) return `${t}s`;
	const m = Math.floor(t / 60);
	const s = t % 60;
	return s ? `${m}m ${s}s` : `${m}m`;
}

export function durationText(seconds: number | null, fractional = false): string {
	if (seconds == null) return '';
	if (seconds < 60) return fractional ? `${seconds.toFixed(1)}s` : `${Math.round(seconds)}s`;
	return formatSeconds(seconds);
}

export function durationLabel(scan: ScanRead, now: number = Date.now()): string {
	const live = elapsedSeconds(scan, now);
	if (live != null) return formatSeconds(live);
	if (scan.duration_seconds == null) return '—';
	return formatSeconds(scan.duration_seconds);
}

export interface CountPill {
	key: string;
	icon: IconComponent;
	label: string;
	value: number;
	emphasis: boolean;
}

export function scanCountPills(scan: ScanRead): CountPill[] {
	return [
		{
			key: 'subs',
			icon: Network,
			label: 'Subdomains',
			value: scan.subdomains_found,
			emphasis: false
		},
		{ key: 'ips', icon: Server, label: 'IPs', value: scan.ips_found, emphasis: false },
		{
			key: 'ports',
			icon: Plug,
			label: 'Open ports',
			value: scan.open_ports_found,
			emphasis: false
		},
		{
			key: 'vulns',
			icon: Bug,
			label: 'Vulnerabilities',
			value: scan.vulnerabilities_found,
			emphasis: scan.vulnerabilities_found > 0
		},
		{
			key: 'endpoints',
			icon: Link2,
			label: 'Endpoints',
			value: scan.endpoints_found,
			emphasis: false
		}
	];
}

function effectiveDuration(scan: ScanRead, now: number): number {
	return elapsedSeconds(scan, now) ?? scan.duration_seconds ?? 0;
}

export function compareScans(
	a: ScanRead,
	b: ScanRead,
	key: ScanSortKey,
	now: number = Date.now()
): number {
	switch (key) {
		case 'duration':
			return effectiveDuration(a, now) - effectiveDuration(b, now);
		case 'status':
			return SCAN_STATUS_RANK[a.status] - SCAN_STATUS_RANK[b.status];
		case 'subdomains':
			return a.subdomains_found - b.subdomains_found;
		case 'vulnerabilities':
			return a.vulnerabilities_found - b.vulnerabilities_found;
		case 'started':
		default: {
			const at = new Date(a.started_at ?? a.created_at).getTime();
			const bt = new Date(b.started_at ?? b.created_at).getTime();
			return at - bt;
		}
	}
}
