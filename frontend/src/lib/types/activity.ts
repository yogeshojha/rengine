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
	scan_id: string | null;
	target_value: string | null;
}

export type ActivityLevel = MessageLevel;

export const ACTIVITY_EVENT = {
	SCAN_STARTED: 'scan.started',
	SCAN_PROGRESS: 'scan.progress',
	SCAN_COMPLETED: 'scan.completed',
	SCAN_FAILED: 'scan.failed',
	SCAN_CANCELLED: 'scan.cancelled',
	SCAN_STAGE_COMPLETED: 'scan.stage.completed',
	SCAN_STAGE_FAILED: 'scan.stage.failed'
} as const;

export const RUN_STATUSES = ['running', 'completed', 'failed', 'cancelled'] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

export interface RunSummary {
	status: RunStatus;
	target: string | null;
	engine: string | null;
	summary: string | null;
	steps: ActivityLog[];
}

export type ActivityClusterKind = 'run' | 'events';

export interface ActivityCluster {
	id: string;
	kind: ActivityClusterKind;
	group: string;
	label: string;
	level: ActivityLevel;
	timestamp: string;
	items: ActivityLog[];
	scanId: string | null;
	targetId: string | null;
	targetLabel: string | null;
	run: RunSummary | null;
}

export const ACTIVITY_GROUPINGS = ['target', 'timeline'] as const;
export type ActivityGrouping = (typeof ACTIVITY_GROUPINGS)[number];
export const DEFAULT_ACTIVITY_GROUPING: ActivityGrouping = 'target';

export const UNSCOPED_GROUP_KEY = 'none';
export const UNSCOPED_GROUP_LABEL = 'Project & system';
export const DELETED_TARGET_LABEL = 'Deleted target';

export interface ActivityTargetGroup {
	key: string;
	label: string;
	targetId: string | null;
	clusters: ActivityCluster[];
	latest: string;
	runs: number;
	errors: number;
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

const TITLE_SEPARATOR = ' · ';

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

export function isRunTerminalEvent(eventType: string): boolean {
	return (
		eventType === ACTIVITY_EVENT.SCAN_COMPLETED ||
		eventType === ACTIVITY_EVENT.SCAN_FAILED ||
		eventType === ACTIVITY_EVENT.SCAN_CANCELLED
	);
}

export function isStageEvent(eventType: string): boolean {
	return (
		eventType === ACTIVITY_EVENT.SCAN_STAGE_COMPLETED ||
		eventType === ACTIVITY_EVENT.SCAN_STAGE_FAILED
	);
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

function clusterLabel(items: ActivityLog[]): string {
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

function titleSuffix(title: string): string | null {
	const idx = title.indexOf(TITLE_SEPARATOR);
	return idx === -1 ? null : title.slice(idx + TITLE_SEPARATOR.length).trim() || null;
}

function buildRun(items: ActivityLog[]): RunSummary {
	const byType = (type: string) => items.find((i) => i.event_type === type);
	const completed = byType(ACTIVITY_EVENT.SCAN_COMPLETED);
	const failed = byType(ACTIVITY_EVENT.SCAN_FAILED);
	const cancelled = byType(ACTIVITY_EVENT.SCAN_CANCELLED);
	const started = byType(ACTIVITY_EVENT.SCAN_STARTED);
	const head = completed ?? failed ?? cancelled ?? started ?? items[0];

	const status: RunStatus = completed
		? 'completed'
		: failed
			? 'failed'
			: cancelled
				? 'cancelled'
				: 'running';

	return {
		status,
		target: titleSuffix(head.title) ?? (started ? titleSuffix(started.title) : null),
		engine: started?.description ?? null,
		summary: completed?.description ?? failed?.description ?? null,
		steps: items
			.filter(
				(i) => !isRunTerminalEvent(i.event_type) && i.event_type !== ACTIVITY_EVENT.SCAN_STARTED
			)
			.reverse()
	};
}

function buildRunCluster(scanId: string, items: ActivityLog[]): ActivityCluster {
	const run = buildRun(items);
	return {
		id: `run:${scanId}`,
		kind: 'run',
		group: `run:${scanId}`,
		label: run.target ?? 'Scan',
		level: dominantLevel(items),
		timestamp: items[0].timestamp,
		items,
		scanId,
		targetId: items.find((i) => i.target_id)?.target_id ?? null,
		targetLabel: run.target ?? items.find((i) => i.target_value)?.target_value ?? null,
		run
	};
}

function buildCluster(items: ActivityLog[], group: string): ActivityCluster {
	return {
		id: items[0].id,
		kind: 'events',
		group,
		label: clusterLabel(items),
		level: dominantLevel(items),
		timestamp: items[0].timestamp,
		items,
		scanId: null,
		targetId: items[0].target_id,
		targetLabel: items.find((i) => i.target_value)?.target_value ?? null,
		run: null
	};
}

export function clusterEvents(events: ActivityLog[]): ActivityCluster[] {
	if (events.length === 0) return [];

	const runs = new Map<string, ActivityLog[]>();
	const loose: ActivityLog[] = [];
	for (const event of events) {
		if (event.scan_id) {
			const list = runs.get(event.scan_id);
			if (list) list.push(event);
			else runs.set(event.scan_id, [event]);
		} else {
			loose.push(event);
		}
	}

	const clusters: ActivityCluster[] = [];
	for (const [scanId, items] of runs) clusters.push(buildRunCluster(scanId, items));

	if (loose.length > 0) {
		let currentKey = getClusterKey(loose[0]);
		let currentItems: ActivityLog[] = [loose[0]];

		for (let i = 1; i < loose.length; i++) {
			const event = loose[i];
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
	}

	return clusters.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
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

export function groupByTarget(clusters: ActivityCluster[]): ActivityTargetGroup[] {
	const groups = new Map<string, ActivityTargetGroup>();
	for (const cluster of clusters) {
		const key = cluster.targetLabel
			? `name:${cluster.targetLabel}`
			: cluster.targetId
				? `id:${cluster.targetId}`
				: UNSCOPED_GROUP_KEY;
		let group = groups.get(key);
		if (!group) {
			group = {
				key,
				label:
					cluster.targetLabel ?? (cluster.targetId ? DELETED_TARGET_LABEL : UNSCOPED_GROUP_LABEL),
				targetId: cluster.targetId,
				clusters: [],
				latest: cluster.timestamp,
				runs: 0,
				errors: 0
			};
			groups.set(key, group);
		} else if (!group.targetId && cluster.targetId) {
			group.targetId = cluster.targetId;
		}
		group.clusters.push(cluster);
		if (cluster.kind === 'run') group.runs++;
		group.errors += cluster.items.filter((i) => i.level === 'error').length;
	}
	return [...groups.values()].sort((a, b) => {
		if (a.key === UNSCOPED_GROUP_KEY) return 1;
		if (b.key === UNSCOPED_GROUP_KEY) return -1;
		return new Date(b.latest).getTime() - new Date(a.latest).getTime();
	});
}
