import Clock from '@lucide/svelte/icons/clock';
import LoaderCircle from '@lucide/svelte/icons/loader-circle';
import CircleCheck from '@lucide/svelte/icons/circle-check';
import CircleX from '@lucide/svelte/icons/circle-x';
import CircleMinus from '@lucide/svelte/icons/circle-minus';
import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
import Ban from '@lucide/svelte/icons/ban';
import Network from '@lucide/svelte/icons/network';
import Server from '@lucide/svelte/icons/server';
import Plug from '@lucide/svelte/icons/plug';
import Globe from '@lucide/svelte/icons/globe';
import Bug from '@lucide/svelte/icons/bug';
import Link2 from '@lucide/svelte/icons/link-2';
import type { ScanActivityStatus, ScanRead, ScanStatus, ScanStatusCounts } from '$lib/types/scan';
import type { BadgeVariant } from '$lib/components/ui/badge';
import type { IconComponent } from '$lib/config/icons';

export const SCAN_STATUS_LABEL: Record<ScanStatus, string> = {
	pending: 'Queued',
	running: 'Running',
	completed: 'Completed',
	failed: 'Failed',
	cancelled: 'Cancelled'
};

export const SCAN_STATUS_VARIANT: Record<ScanStatus, BadgeVariant> = {
	pending: 'secondary',
	running: 'info',
	completed: 'success',
	failed: 'destructive',
	cancelled: 'outline'
};

export function scanStatusVariant(s: ScanStatus): BadgeVariant {
	return SCAN_STATUS_VARIANT[s];
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

export type ScanStatusTab = 'all' | 'active' | 'completed' | 'failed' | 'cancelled';

export const SCAN_STATUS_TABS: { key: ScanStatusTab; label: string; statuses: ScanStatus[] }[] = [
	{ key: 'all', label: 'All', statuses: [] },
	{ key: 'active', label: 'Active', statuses: ['running', 'pending'] },
	{ key: 'completed', label: 'Completed', statuses: ['completed'] },
	{ key: 'failed', label: 'Failed', statuses: ['failed'] },
	{ key: 'cancelled', label: 'Cancelled', statuses: ['cancelled'] }
];

const tabKey = (statuses: ScanStatus[]) => [...statuses].sort().join(',');

export function scanStatusTab(statuses: ScanStatus[]): ScanStatusTab {
	const key = tabKey(statuses);
	return SCAN_STATUS_TABS.find((t) => tabKey(t.statuses) === key)?.key ?? 'all';
}

export function scanStatusTabCount(
	tab: ScanStatusTab,
	counts: ScanStatusCounts,
	total: number
): number {
	if (tab === 'all') return total;
	const statuses = SCAN_STATUS_TABS.find((t) => t.key === tab)?.statuses ?? [];
	return statuses.reduce((n, s) => n + counts[s], 0);
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
			return 'text-warning';
		case 'success':
			return 'text-success';
		case 'running':
			return 'text-info';
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
export const RESULTS_PAGE_SIZE = 50;
export const SEARCH_DEBOUNCE_MS = 220;
export const RESULTS_SCROLL = 'max-h-[calc(100svh-25rem)] min-h-[15rem]';

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
			key: 'http',
			icon: Globe,
			label: 'HTTP services',
			value: scan.http_assets_found,
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
