import { MS_PER_DAY } from '$lib/utilities/dates';
import type { MessageLevel } from '$lib/types/message-level';

export interface ActivityLog {
	id: string;
	timestamp: string;
	level: ActivityLevel;
	event_type: string;
	title: string;
	description: string | null;
	project_id: string | null;
	target_id: string | null;
	user_id: string | null;
}

export type ActivityLevel = MessageLevel;

export interface ActivityCluster {
	id: string;
	group: string;
	label: string;
	level: ActivityLevel;
	timestamp: string;
	items: ActivityLog[];
}

export interface ActivityDayGroup {
	label: string;
	date: string;
	clusters: ActivityCluster[];
}

interface ParsedEventType {
	entity: string;
	group: string | null;
	detail: string | null;
	action: string;
}

function parseEventType(eventType: string): ParsedEventType {
	const parts = eventType.split('.');
	if (parts.length >= 4) {
		return {
			entity: parts[0],
			group: parts[1],
			detail: parts[2],
			action: parts[3]
		};
	}
	if (parts.length === 3) {
		return {
			entity: parts[0],
			group: parts[1],
			detail: null,
			action: parts[2]
		};
	}
	return {
		entity: parts[0],
		group: null,
		detail: null,
		action: parts[parts.length - 1]
	};
}

function getClusterKey(event: ActivityLog): string {
	const parsed = parseEventType(event.event_type);
	const scope = event.target_id ?? event.project_id ?? 'global';
	if (parsed.group) {
		return `${parsed.entity}.${parsed.group}:${scope}`;
	}
	return `${event.id}`;
}

const CLUSTER_WINDOW_MS = 60_000;

export function getCategoryLabel(eventType: string): string {
	const parsed = parseEventType(eventType);
	if (parsed.group) return parsed.group.toUpperCase();
	return parsed.entity.toUpperCase();
}

function dominantLevel(items: ActivityLog[]): ActivityLevel {
	const priority: Record<ActivityLevel, number> = {
		error: 3,
		warning: 2,
		success: 1,
		info: 0
	};
	let max: ActivityLevel = 'info';
	for (const item of items) {
		if (priority[item.level] > priority[max]) {
			max = item.level;
		}
	}
	return max;
}

function pluralize(word: string, count: number): string {
	if (count === 1) return word;

	if (word.endsWith('s') || word.endsWith('x') || word.endsWith('z')) return word;

	return `${word}s`;
}

function clusterLabel(items: ActivityLog[], _group: string): string {
	if (items.length === 1) return items[0].title;
	const parsed = parseEventType(items[0].event_type);
	const groupName = parsed.group ?? parsed.entity;
	const noun = pluralize(groupName, items.length);

	const failed = items.filter((i) => i.level === 'error').length;
	const succeeded = items.length - failed;

	if (failed > 0 && succeeded > 0) {
		return `${succeeded} ${noun} completed, ${failed} failed`;
	}
	if (failed > 0) {
		return `${failed} ${noun} failed`;
	}
	return `${items.length} ${noun} completed`;
}

export function clusterEvents(events: ActivityLog[]): ActivityCluster[] {
	if (events.length === 0) return [];

	const clusters: ActivityCluster[] = [];
	let currentKey = getClusterKey(events[0]);
	let currentItems: ActivityLog[] = [events[0]];

	for (let i = 1; i < events.length; i++) {
		const event = events[i];
		const key = getClusterKey(event);
		const timeDiff = Math.abs(
			new Date(currentItems[0].timestamp).getTime() - new Date(event.timestamp).getTime()
		);

		if (key === currentKey && timeDiff <= CLUSTER_WINDOW_MS) {
			currentItems.push(event);
		} else {
			clusters.push(buildCluster(currentItems, currentKey));
			currentKey = key;
			currentItems = [event];
		}
	}

	clusters.push(buildCluster(currentItems, currentKey));
	return clusters;
}

function buildCluster(items: ActivityLog[], group: string): ActivityCluster {
	return {
		id: items[0].id,
		group,
		label: clusterLabel(items, group),
		level: dominantLevel(items),
		timestamp: items[0].timestamp,
		items
	};
}

export function groupByDay(clusters: ActivityCluster[]): ActivityDayGroup[] {
	const groups: Map<string, ActivityCluster[]> = new Map();

	for (const cluster of clusters) {
		const date = new Date(cluster.timestamp);
		const key = date.toISOString().split('T')[0];
		if (!groups.has(key)) {
			groups.set(key, []);
		}
		groups.get(key)!.push(cluster);
	}

	const today = new Date().toISOString().split('T')[0];
	const yesterday = new Date(Date.now() - MS_PER_DAY).toISOString().split('T')[0];

	return Array.from(groups.entries()).map(([date, dayClusters]) => ({
		label:
			date === today
				? 'Today'
				: date === yesterday
					? 'Yesterday'
					: new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
							month: 'short',
							day: 'numeric'
						}),
		date,
		clusters: dayClusters
	}));
}
