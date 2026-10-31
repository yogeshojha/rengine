// mirrors shared/definitions/timeline.py
import type { SortOption } from '$lib/components/scans/results/table/columns';

export enum WebAssetState {
	LIVE = 'live',
	REDIRECT = 'redirect',
	CLIENT_ERROR = 'client_error',
	SERVER_ERROR = 'server_error',
	NO_HTTP = 'no_http',
	UNRESOLVED = 'unresolved',
	GONE = 'gone',
	UNCONFIRMED = 'unconfirmed',
	UNOBSERVED = 'unobserved',
	UNSEEN = 'unseen'
}

export const WEB_STATE_LABELS: Record<WebAssetState, string> = {
	[WebAssetState.LIVE]: 'Live',
	[WebAssetState.REDIRECT]: 'Redirect',
	[WebAssetState.CLIENT_ERROR]: 'Client error',
	[WebAssetState.SERVER_ERROR]: 'Server error',
	[WebAssetState.NO_HTTP]: 'No HTTP',
	[WebAssetState.UNRESOLVED]: 'Unresolved',
	[WebAssetState.GONE]: 'Gone',
	[WebAssetState.UNCONFIRMED]: 'Not confirmed',
	[WebAssetState.UNOBSERVED]: 'Not observed',
	[WebAssetState.UNSEEN]: 'Not yet seen'
};

// the states that say nothing about the host itself
export const SILENT_STATES: ReadonlySet<string> = new Set([
	WebAssetState.UNCONFIRMED,
	WebAssetState.UNOBSERVED
]);

export const ABSENT_STATES: ReadonlySet<string> = new Set([
	WebAssetState.GONE,
	WebAssetState.UNSEEN
]);

const HATCH = 'bg-[repeating-linear-gradient(135deg,var(--fill-hatch)_0_2px,transparent_2px_5px)]';

// one cell of a strip
export const STATE_CELL: Record<WebAssetState, string> = {
	[WebAssetState.LIVE]: 'bg-fill-success',
	[WebAssetState.REDIRECT]: 'bg-fill-info',
	[WebAssetState.CLIENT_ERROR]: 'bg-fill-warning',
	[WebAssetState.SERVER_ERROR]: 'bg-fill-destructive',
	[WebAssetState.NO_HTTP]: 'bg-fill-muted',
	[WebAssetState.UNRESOLVED]: 'bg-fill-strong',
	[WebAssetState.GONE]: 'border border-dashed border-fill-strong/60',
	[WebAssetState.UNCONFIRMED]: `border border-dashed border-fill-hatch ${HATCH}`,
	[WebAssetState.UNOBSERVED]: HATCH,
	[WebAssetState.UNSEEN]: ''
};

// the dot beside a state label
export const STATE_DOT: Record<WebAssetState, string> = {
	[WebAssetState.LIVE]: 'bg-fill-success',
	[WebAssetState.REDIRECT]: 'bg-fill-info',
	[WebAssetState.CLIENT_ERROR]: 'bg-fill-warning',
	[WebAssetState.SERVER_ERROR]: 'bg-fill-destructive',
	[WebAssetState.NO_HTTP]: 'bg-fill-muted',
	[WebAssetState.UNRESOLVED]: 'bg-fill-strong',
	[WebAssetState.GONE]: 'border border-dashed border-fill-strong/70',
	[WebAssetState.UNCONFIRMED]: 'border border-dashed border-fill-hatch',
	[WebAssetState.UNOBSERVED]: HATCH,
	[WebAssetState.UNSEEN]: 'border border-border'
};

// the query a legend item applies
export const STATE_QUERY: Partial<Record<WebAssetState, string>> = {
	[WebAssetState.LIVE]: 'status:2xx',
	[WebAssetState.REDIRECT]: 'status:3xx',
	[WebAssetState.CLIENT_ERROR]: 'status:4xx',
	[WebAssetState.SERVER_ERROR]: 'status:5xx',
	[WebAssetState.NO_HTTP]: 'is:resolved not is:web',
	[WebAssetState.UNRESOLVED]: 'not is:resolved'
};

// the legend, in reading order
export const LEGEND_STATES: WebAssetState[] = [
	WebAssetState.LIVE,
	WebAssetState.REDIRECT,
	WebAssetState.CLIENT_ERROR,
	WebAssetState.SERVER_ERROR,
	WebAssetState.NO_HTTP,
	WebAssetState.UNRESOLVED,
	WebAssetState.GONE,
	WebAssetState.UNCONFIRMED,
	WebAssetState.UNOBSERVED,
	WebAssetState.UNSEEN
];

export enum Observation {
	OBSERVED = 'observed',
	PARTIAL = 'partial',
	UNOBSERVED = 'unobserved'
}

export const OBSERVATION_LABELS: Record<Observation, string> = {
	[Observation.OBSERVED]: 'Observed',
	[Observation.PARTIAL]: 'Discovery partial',
	[Observation.UNOBSERVED]: 'Not observed'
};

export enum TimelineFlag {
	NEW = 'new',
	GONE = 'gone',
	CHANGED = 'changed',
	EPHEMERAL = 'ephemeral',
	FLAPPING = 'flapping',
	ATTRIBUTE = 'attribute'
}

export const FLAG_ORDER: TimelineFlag[] = [
	TimelineFlag.NEW,
	TimelineFlag.GONE,
	TimelineFlag.CHANGED,
	TimelineFlag.EPHEMERAL,
	TimelineFlag.FLAPPING,
	TimelineFlag.ATTRIBUTE
];

export const FLAG_LABELS: Record<TimelineFlag, string> = {
	[TimelineFlag.NEW]: 'New in this scan',
	[TimelineFlag.GONE]: 'Gone',
	[TimelineFlag.CHANGED]: 'Changed',
	[TimelineFlag.EPHEMERAL]: 'Ephemeral',
	[TimelineFlag.FLAPPING]: 'Flapping',
	[TimelineFlag.ATTRIBUTE]: 'Attribute changed'
};

export const FLAG_HELP: Record<TimelineFlag, string> = {
	[TimelineFlag.NEW]: 'First seen in this scan.',
	[TimelineFlag.GONE]: 'Absent from this scan after an earlier sighting.',
	[TimelineFlag.CHANGED]: 'At least one transition in the window.',
	[TimelineFlag.EPHEMERAL]: 'Appeared and gone inside the window.',
	[TimelineFlag.FLAPPING]: 'Three or more state transitions in the window.',
	[TimelineFlag.ATTRIBUTE]:
		'Title, address, redirect, server, WAF, CDN or certificate changed with the state unchanged.'
};

export const TIMELINE_WINDOWS = [10, 25, 50] as const;
export const DEFAULT_TIMELINE_WINDOW = 25;

export enum TimelineSort {
	LAST_CHANGE = 'last_change',
	CHANGES = 'changes',
	FIRST_SEEN = 'first_seen',
	NAME = 'name',
	STATUS = 'status'
}

export const TIMELINE_SORTS: SortOption[] = [
	{ key: TimelineSort.LAST_CHANGE, label: 'Last change' },
	{ key: TimelineSort.CHANGES, label: 'Changes' },
	{ key: TimelineSort.FIRST_SEEN, label: 'First seen' },
	{ key: TimelineSort.NAME, label: 'Host' },
	{ key: TimelineSort.STATUS, label: 'Status' }
];

export const DEFAULT_TIMELINE_SORT = { key: TimelineSort.LAST_CHANGE, dir: -1 as const };

export const TIMELINE_VIEW = 'timeline';

// ---------- renders ----------

export enum RenderState {
	FIRST = 'first',
	CHANGED = 'changed',
	SAME = 'same',
	NOT_CAPTURED = 'not_captured',
	NO_HTTP = 'no_http',
	GONE = 'gone',
	UNCONFIRMED = 'unconfirmed',
	UNOBSERVED = 'unobserved',
	UNSEEN = 'unseen'
}

export const CAPTURED_STATES: ReadonlySet<string> = new Set([
	RenderState.FIRST,
	RenderState.CHANGED,
	RenderState.SAME
]);

export const RENDER_STATE_LABELS: Record<RenderState, string> = {
	[RenderState.FIRST]: 'First screenshot',
	[RenderState.CHANGED]: 'Changed',
	[RenderState.SAME]: 'Unchanged',
	[RenderState.NOT_CAPTURED]: 'No screenshot',
	[RenderState.NO_HTTP]: 'No HTTP',
	[RenderState.GONE]: 'Gone',
	[RenderState.UNCONFIRMED]: 'Not confirmed',
	[RenderState.UNOBSERVED]: 'Not observed',
	[RenderState.UNSEEN]: 'Not yet seen'
};

export const RENDER_OBSERVATION_LABELS: Record<Observation, string> = {
	[Observation.OBSERVED]: 'Observed',
	[Observation.PARTIAL]: 'Some screenshots missing',
	[Observation.UNOBSERVED]: 'No screenshots in this run'
};

// one cell of a render strip
export const RENDER_CELL: Record<RenderState, string> = {
	[RenderState.FIRST]: 'bg-fill-muted',
	[RenderState.CHANGED]: 'bg-fill-strong',
	[RenderState.SAME]: 'bg-fill-muted/50',
	[RenderState.NOT_CAPTURED]: 'border border-dashed border-fill-strong/60',
	[RenderState.NO_HTTP]: 'border border-border',
	[RenderState.GONE]: '',
	[RenderState.UNCONFIRMED]: `border border-dashed border-fill-hatch ${HATCH}`,
	[RenderState.UNOBSERVED]: HATCH,
	[RenderState.UNSEEN]: ''
};

export const RENDER_LEGEND: RenderState[] = [
	RenderState.SAME,
	RenderState.CHANGED,
	RenderState.FIRST,
	RenderState.NOT_CAPTURED,
	RenderState.NO_HTTP,
	RenderState.UNCONFIRMED,
	RenderState.UNOBSERVED
];

export enum RenderFlag {
	NEW = 'new',
	CHANGED = 'changed',
	FLAPPING = 'flapping',
	EXPIRED = 'expired',
	NOT_CAPTURED = 'not_captured'
}

export const RENDER_FLAG_ORDER: RenderFlag[] = [
	RenderFlag.NEW,
	RenderFlag.CHANGED,
	RenderFlag.FLAPPING,
	RenderFlag.EXPIRED,
	RenderFlag.NOT_CAPTURED
];

export const RENDER_FLAG_LABELS: Record<RenderFlag, string> = {
	[RenderFlag.NEW]: 'First screenshot',
	[RenderFlag.CHANGED]: 'Changed',
	[RenderFlag.FLAPPING]: 'Keeps changing',
	[RenderFlag.EXPIRED]: 'Image removed',
	[RenderFlag.NOT_CAPTURED]: 'No screenshot'
};

export const RENDER_FLAG_HELP: Record<RenderFlag, string> = {
	[RenderFlag.NEW]: 'The first screenshot of this web asset was taken in this scan.',
	[RenderFlag.CHANGED]: 'The page looked different in at least one run of the window.',
	[RenderFlag.FLAPPING]: 'The page looked different three or more times in the window.',
	[RenderFlag.EXPIRED]: 'Retention removed an older image in the window.',
	[RenderFlag.NOT_CAPTURED]: 'Answered HTTP in this scan with no screenshot taken.'
};

export enum RenderSort {
	LAST_CHANGE = 'last_change',
	CHANGES = 'changes',
	FIRST_CAPTURED = 'first_captured',
	NAME = 'name',
	STATUS = 'status'
}

export const RENDER_SORTS: SortOption[] = [
	{ key: RenderSort.LAST_CHANGE, label: 'Last change' },
	{ key: RenderSort.CHANGES, label: 'Changes' },
	{ key: RenderSort.FIRST_CAPTURED, label: 'First screenshot' },
	{ key: RenderSort.NAME, label: 'Host' },
	{ key: RenderSort.STATUS, label: 'Status' }
];

export const DEFAULT_RENDER_SORT = { key: RenderSort.LAST_CHANGE, dir: -1 as const };

export const RENDERS_VIEW = 'screenshots';
