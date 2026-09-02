import type { MessageLevel } from '$lib/types/message-level';
import type { Notification } from '$lib/types/notification';
import { MS_PER_DAY } from '$lib/utilities/dates';

export interface NotificationGroup {
	label: string;
	items: Notification[];
}

const RECENCY_LABELS = ['Today', 'Yesterday', 'Earlier'] as const;

export function groupByRecency(items: Notification[]): NotificationGroup[] {
	const startOfToday = new Date();
	startOfToday.setHours(0, 0, 0, 0);
	const today = startOfToday.getTime();
	const yesterday = today - MS_PER_DAY;

	const buckets = new Map<string, Notification[]>(RECENCY_LABELS.map((l) => [l, []]));
	for (const n of items) {
		const t = new Date(n.created_at).getTime();
		const label = t >= today ? 'Today' : t >= yesterday ? 'Yesterday' : 'Earlier';
		buckets.get(label)!.push(n);
	}
	return [...buckets.entries()]
		.filter(([, list]) => list.length > 0)
		.map(([label, list]) => ({ label, items: list }));
}

const SEVERITY_RANK: Record<MessageLevel, number> = { error: 3, warning: 2, success: 1, info: 0 };

export function highestSeverity(items: Notification[]): MessageLevel | null {
	let top: MessageLevel | null = null;
	for (const n of items) {
		if (top === null || SEVERITY_RANK[n.severity] > SEVERITY_RANK[top]) top = n.severity;
	}
	return top;
}

export const UNREAD_BADGE_CLASS: Record<MessageLevel, string> = {
	error: 'bg-destructive text-destructive-foreground',
	warning: 'bg-warning text-warning-foreground',
	success: 'bg-primary text-primary-foreground',
	info: 'bg-primary text-primary-foreground'
};
