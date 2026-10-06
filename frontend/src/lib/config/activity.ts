import ListPlus from '@lucide/svelte/icons/list-plus';
import Pause from '@lucide/svelte/icons/pause';
import Radar from '@lucide/svelte/icons/radar';
import Target from '@lucide/svelte/icons/crosshair';
import Ticket from '@lucide/svelte/icons/ticket';
import type { IconComponent } from '$lib/config/icons';
import type { ScanStatus } from '$lib/types/scan';

// mirrors shared/definitions/activity.py:FEED_EVENTS
export const ACTIVITY_EVENT = {
	SCAN_COMPLETED: 'scan.completed',
	SCAN_FAILED: 'scan.failed',
	SCAN_CANCELLED: 'scan.cancelled',
	SCAN_PAUSED: 'scan.paused',
	SCAN_RESUMED: 'scan.resumed',
	ISSUE_FILED: 'issue.filed',
	ISSUE_FAILED: 'issue.failed',
	TARGET_CREATED: 'target.created',
	TARGET_BULK_IMPORTED: 'target.bulk_imported'
} as const;
export type ActivityEvent = (typeof ACTIVITY_EVENT)[keyof typeof ACTIVITY_EVENT];

export type ActivityTone = 'neutral' | 'warning' | 'error';

export interface ActivityKind {
	icon: IconComponent;
	tone: ActivityTone;
	// the lead is the target, else the row's title
	byTarget: boolean;
	run?: ScanStatus;
	status?: string;
	failure?: boolean;
}

export const ACTIVITY_KINDS: Record<ActivityEvent, ActivityKind> = {
	[ACTIVITY_EVENT.SCAN_COMPLETED]: {
		icon: Radar,
		tone: 'neutral',
		byTarget: true,
		run: 'completed'
	},
	[ACTIVITY_EVENT.SCAN_FAILED]: {
		icon: Radar,
		tone: 'error',
		byTarget: true,
		run: 'failed',
		failure: true
	},
	[ACTIVITY_EVENT.SCAN_CANCELLED]: {
		icon: Radar,
		tone: 'warning',
		byTarget: true,
		run: 'cancelled'
	},
	[ACTIVITY_EVENT.SCAN_PAUSED]: { icon: Pause, tone: 'neutral', byTarget: true, run: 'paused' },
	[ACTIVITY_EVENT.SCAN_RESUMED]: { icon: Radar, tone: 'neutral', byTarget: true, run: 'running' },
	[ACTIVITY_EVENT.ISSUE_FILED]: { icon: Ticket, tone: 'neutral', byTarget: false },
	[ACTIVITY_EVENT.ISSUE_FAILED]: { icon: Ticket, tone: 'error', byTarget: false, failure: true },
	[ACTIVITY_EVENT.TARGET_CREATED]: {
		icon: Target,
		tone: 'neutral',
		byTarget: true,
		status: 'Added'
	},
	[ACTIVITY_EVENT.TARGET_BULK_IMPORTED]: { icon: ListPlus, tone: 'neutral', byTarget: false }
};

export const ACTIVITY_PAGE_SIZE = 30;
export const ACTIVITY_LIVE_CARDS = 4;
