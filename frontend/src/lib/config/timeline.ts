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

export const HATCH =
	'bg-[repeating-linear-gradient(135deg,var(--fill-hatch)_0_2px,transparent_2px_5px)]';

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

// ---------- services ----------

export enum ServiceTimelineMode {
	ADDRESS = 'address',
	PORT = 'port'
}

export const SERVICE_MODE_LABELS: Record<ServiceTimelineMode, string> = {
	[ServiceTimelineMode.ADDRESS]: 'By address',
	[ServiceTimelineMode.PORT]: 'By port'
};

export enum AddressState {
	SAME = 'same',
	OPENED = 'opened',
	CLOSED = 'closed',
	BOTH = 'both',
	FIRST = 'first',
	GONE = 'gone',
	UNCONFIRMED = 'unconfirmed',
	UNOBSERVED = 'unobserved',
	UNSEEN = 'unseen'
}

export const ADDRESS_STATE_LABELS: Record<AddressState, string> = {
	[AddressState.SAME]: 'Same ports',
	[AddressState.OPENED]: 'Port opened',
	[AddressState.CLOSED]: 'Port closed',
	[AddressState.BOTH]: 'Opened and closed',
	[AddressState.FIRST]: 'First seen',
	[AddressState.GONE]: 'Gone',
	[AddressState.UNCONFIRMED]: 'Not confirmed',
	[AddressState.UNOBSERVED]: 'Ports not scanned',
	[AddressState.UNSEEN]: 'Not yet seen'
};

// one cell of an address strip
export const ADDRESS_CELL: Record<AddressState, string> = {
	[AddressState.SAME]: 'bg-fill-muted/50',
	[AddressState.OPENED]: 'bg-fill-strong',
	[AddressState.CLOSED]: 'border border-dashed border-fill-strong',
	[AddressState.BOTH]:
		'border border-dashed border-fill-strong bg-[linear-gradient(90deg,var(--fill-strong)_50%,transparent_50%)]',
	[AddressState.FIRST]: 'bg-fill-muted',
	[AddressState.GONE]: '',
	[AddressState.UNCONFIRMED]: `border border-dashed border-fill-hatch ${HATCH}`,
	[AddressState.UNOBSERVED]: HATCH,
	[AddressState.UNSEEN]: ''
};

export const ADDRESS_LEGEND: AddressState[] = [
	AddressState.SAME,
	AddressState.OPENED,
	AddressState.CLOSED,
	AddressState.BOTH,
	AddressState.FIRST,
	AddressState.UNCONFIRMED,
	AddressState.UNOBSERVED
];

export enum LaneState {
	OPEN = 'open',
	CLOSED = 'closed',
	UNCONFIRMED = 'unconfirmed',
	UNOBSERVED = 'unobserved',
	UNSEEN = 'unseen'
}

export const LANE_STATE_LABELS: Record<LaneState, string> = {
	[LaneState.OPEN]: 'Open',
	[LaneState.CLOSED]: 'Closed',
	[LaneState.UNCONFIRMED]: 'Not confirmed',
	[LaneState.UNOBSERVED]: 'Ports not scanned',
	[LaneState.UNSEEN]: 'Not yet seen'
};

export const LANE_CELL: Record<LaneState, string> = {
	[LaneState.OPEN]: 'bg-fill-strong',
	[LaneState.CLOSED]: 'border border-border',
	[LaneState.UNCONFIRMED]: `border border-dashed border-fill-hatch ${HATCH}`,
	[LaneState.UNOBSERVED]: HATCH,
	[LaneState.UNSEEN]: ''
};

export const SERVICE_OBSERVATION_LABELS: Record<Observation, string> = {
	[Observation.OBSERVED]: 'Ports scanned',
	[Observation.PARTIAL]: 'Port scan partial',
	[Observation.UNOBSERVED]: 'Ports not scanned in this run'
};

export enum AddressFlag {
	OPENED = 'opened',
	CLOSED = 'closed',
	NEW = 'new',
	GONE = 'gone',
	SOFTWARE = 'software',
	FLAPPING = 'flapping'
}

export const ADDRESS_FLAG_ORDER: AddressFlag[] = [
	AddressFlag.OPENED,
	AddressFlag.CLOSED,
	AddressFlag.NEW,
	AddressFlag.GONE,
	AddressFlag.SOFTWARE,
	AddressFlag.FLAPPING
];

export const ADDRESS_FLAG_LABELS: Record<AddressFlag, string> = {
	[AddressFlag.OPENED]: 'Ports opened',
	[AddressFlag.CLOSED]: 'Ports closed',
	[AddressFlag.NEW]: 'New address',
	[AddressFlag.GONE]: 'Gone',
	[AddressFlag.SOFTWARE]: 'Software changed',
	[AddressFlag.FLAPPING]: 'Keeps changing'
};

export const ADDRESS_FLAG_HELP: Record<AddressFlag, string> = {
	[AddressFlag.OPENED]: 'A port opened on the address inside the window.',
	[AddressFlag.CLOSED]: 'A port closed on the address inside the window.',
	[AddressFlag.NEW]: 'The address answered on a port for the first time in this scan.',
	[AddressFlag.GONE]: 'No port answers on the address in this scan.',
	[AddressFlag.SOFTWARE]: 'A service on the address reported different software.',
	[AddressFlag.FLAPPING]: 'One port opened and closed three or more times in the window.'
};

export enum PortFlag {
	SPREAD = 'spread',
	SHRANK = 'shrank',
	NEW = 'new',
	GONE = 'gone'
}

export const PORT_FLAG_ORDER: PortFlag[] = [
	PortFlag.SPREAD,
	PortFlag.SHRANK,
	PortFlag.NEW,
	PortFlag.GONE
];

export const PORT_FLAG_LABELS: Record<PortFlag, string> = {
	[PortFlag.SPREAD]: 'Spread',
	[PortFlag.SHRANK]: 'Shrank',
	[PortFlag.NEW]: 'New on target',
	[PortFlag.GONE]: 'Gone'
};

export const PORT_FLAG_HELP: Record<PortFlag, string> = {
	[PortFlag.SPREAD]: 'The port opened on more addresses inside the window.',
	[PortFlag.SHRANK]: 'The port closed on some addresses inside the window.',
	[PortFlag.NEW]: 'The port answered on this target for the first time in this scan.',
	[PortFlag.GONE]: 'No address answers on the port in this scan.'
};

export enum AddressSort {
	LAST_CHANGE = 'last_change',
	CHANGES = 'changes',
	FIRST_SEEN = 'first_seen',
	OPEN = 'open',
	ADDRESS = 'address'
}

export const ADDRESS_SORTS: SortOption[] = [
	{ key: AddressSort.LAST_CHANGE, label: 'Last change' },
	{ key: AddressSort.CHANGES, label: 'Changes' },
	{ key: AddressSort.FIRST_SEEN, label: 'First seen' },
	{ key: AddressSort.OPEN, label: 'Open ports' },
	{ key: AddressSort.ADDRESS, label: 'Address' }
];

export enum PortSort {
	ADDRESSES = 'addresses',
	LAST_CHANGE = 'last_change',
	FIRST_SEEN = 'first_seen',
	PORT = 'port'
}

export const PORT_SORTS: SortOption[] = [
	{ key: PortSort.ADDRESSES, label: 'Addresses' },
	{ key: PortSort.LAST_CHANGE, label: 'Last change' },
	{ key: PortSort.FIRST_SEEN, label: 'First seen' },
	{ key: PortSort.PORT, label: 'Port' }
];

export const DEFAULT_ADDRESS_SORT = { key: AddressSort.LAST_CHANGE, dir: -1 as const };
export const DEFAULT_PORT_SORT = { key: PortSort.ADDRESSES, dir: -1 as const };

export const SERVICES_TIMELINE_VIEW = 'timeline';

// ---------- findings ----------

export enum FindingTimelineMode {
	LIFESPANS = 'lifespans',
	CHECKS = 'checks'
}

export const FINDING_MODE_LABELS: Record<FindingTimelineMode, string> = {
	[FindingTimelineMode.LIFESPANS]: 'Lifespans',
	[FindingTimelineMode.CHECKS]: 'By check'
};

export enum FindingState {
	OPEN = 'open',
	REGRESSED = 'regressed',
	FIXED = 'fixed',
	NOT_TESTED = 'not_tested',
	UNOBSERVED = 'unobserved',
	UNSEEN = 'unseen'
}

export const PRESENT_STATES: FindingState[] = [FindingState.OPEN, FindingState.REGRESSED];

export const FINDING_STATE_LABELS: Record<FindingState, string> = {
	[FindingState.OPEN]: 'Open',
	[FindingState.REGRESSED]: 'Came back',
	[FindingState.FIXED]: 'Fixed',
	[FindingState.NOT_TESTED]: 'Not tested',
	[FindingState.UNOBSERVED]: 'No vulnerability scan',
	[FindingState.UNSEEN]: 'Not seen yet'
};

export const FINDING_OBSERVATION_LABELS: Record<Observation, string> = {
	[Observation.OBSERVED]: 'Vulnerability scan completed',
	[Observation.PARTIAL]: 'Vulnerability scan incomplete',
	[Observation.UNOBSERVED]: 'No vulnerability scan in this run'
};

export enum FindingGroup {
	REGRESSED = 'regressed',
	NEW = 'new',
	OPEN = 'open',
	FIXED = 'fixed',
	SET_ASIDE = 'set_aside'
}

export const FINDING_GROUP_ORDER: FindingGroup[] = [
	FindingGroup.REGRESSED,
	FindingGroup.NEW,
	FindingGroup.OPEN,
	FindingGroup.FIXED,
	FindingGroup.SET_ASIDE
];

export const FINDING_GROUP_LABELS: Record<FindingGroup, string> = {
	[FindingGroup.REGRESSED]: 'Regressed',
	[FindingGroup.NEW]: 'New in this scan',
	[FindingGroup.OPEN]: 'Open',
	[FindingGroup.FIXED]: 'Fixed',
	[FindingGroup.SET_ASIDE]: 'Set aside'
};

export const FINDING_GROUP_HELP: Record<FindingGroup, string> = {
	[FindingGroup.REGRESSED]: 'Came back after a run that found it fixed.',
	[FindingGroup.NEW]: 'First seen in this scan.',
	[FindingGroup.OPEN]: 'Found in this scan, or absent with the check untested since.',
	[FindingGroup.FIXED]: 'A later run tested for it and found nothing.',
	[FindingGroup.SET_ASIDE]: 'Reviewed as a false positive or an accepted risk.'
};

export enum FindingSort {
	AGE = 'age',
	LAST_CHANGE = 'last_change',
	SEVERITY = 'severity',
	FIRST_SEEN = 'first_seen',
	NAME = 'name'
}

export const FINDING_SORTS: SortOption[] = [
	{ key: FindingSort.AGE, label: 'Days open' },
	{ key: FindingSort.LAST_CHANGE, label: 'Last change' },
	{ key: FindingSort.SEVERITY, label: 'Severity' },
	{ key: FindingSort.FIRST_SEEN, label: 'First seen' },
	{ key: FindingSort.NAME, label: 'Check' }
];

export enum CheckState {
	TESTED = 'tested',
	NOT_TESTED = 'not_tested',
	NOT_IN_LIBRARY = 'not_in_library',
	UNOBSERVED = 'unobserved'
}

export const CHECK_STATE_LABELS: Record<CheckState, string> = {
	[CheckState.TESTED]: 'Tested',
	[CheckState.NOT_TESTED]: 'Not tested',
	[CheckState.NOT_IN_LIBRARY]: 'Check not in the library yet',
	[CheckState.UNOBSERVED]: 'No vulnerability scan'
};

export enum CheckFlag {
	SPREAD = 'spread',
	SHRANK = 'shrank',
	CLEARED = 'cleared',
	LIBRARY_NEW = 'library_new'
}

export const CHECK_FLAG_ORDER: CheckFlag[] = [
	CheckFlag.SPREAD,
	CheckFlag.SHRANK,
	CheckFlag.CLEARED,
	CheckFlag.LIBRARY_NEW
];

export const CHECK_FLAG_LABELS: Record<CheckFlag, string> = {
	[CheckFlag.SPREAD]: 'Spread',
	[CheckFlag.SHRANK]: 'Shrank',
	[CheckFlag.CLEARED]: 'Cleared',
	[CheckFlag.LIBRARY_NEW]: 'New to the library'
};

export const CHECK_FLAG_HELP: Record<CheckFlag, string> = {
	[CheckFlag.SPREAD]:
		'The check matches more web assets than in the first run of the window that found it.',
	[CheckFlag.SHRANK]:
		'The check matches fewer web assets than in the first run of the window that found it.',
	[CheckFlag.CLEARED]: 'No web asset carries the finding in this scan.',
	[CheckFlag.LIBRARY_NEW]: 'The library gained the check inside the window.'
};

export enum CheckSort {
	HOSTS = 'hosts',
	SEVERITY = 'severity',
	LAST_CHANGE = 'last_change',
	NAME = 'name'
}

export const CHECK_SORTS: SortOption[] = [
	{ key: CheckSort.HOSTS, label: 'Hosts' },
	{ key: CheckSort.SEVERITY, label: 'Severity' },
	{ key: CheckSort.LAST_CHANGE, label: 'Last change' },
	{ key: CheckSort.NAME, label: 'Check' }
];

export const DEFAULT_FINDING_SORT = { key: FindingSort.AGE, dir: -1 as const };
export const DEFAULT_CHECK_SORT = { key: CheckSort.HOSTS, dir: -1 as const };

export const FINDINGS_TIMELINE_VIEW = 'timeline';

export const CHECK_CELL: Record<CheckState, string> = {
	[CheckState.TESTED]: 'bg-fill-muted/40',
	[CheckState.NOT_TESTED]: HATCH,
	[CheckState.NOT_IN_LIBRARY]: 'border border-dotted border-fill-hatch',
	[CheckState.UNOBSERVED]: `${HATCH} opacity-60`
};

export const SEGMENT_HATCH =
	'repeating-linear-gradient(135deg, var(--fill-hatch) 0 3px, transparent 3px 6px)';
export const SEGMENT_DASH =
	'repeating-linear-gradient(90deg, var(--fill-strong) 0 6px, transparent 6px 10px)';
