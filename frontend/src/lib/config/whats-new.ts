// mirrors shared/definitions/whats_new.py
import { SurfaceDimension } from './surface';
import { Severity } from './vulnerabilities';
import type { ScanStatus } from '$lib/types/scan';

export const NewKind = {
	FINDING: 'finding',
	PROGRAM: 'program',
	SCOPE: 'scope',
	OUT_OF_SCOPE: 'out_of_scope',
	BOUNTY_TABLE: 'bounty_table',
	RULES: 'rules',
	CERT_HOST: 'cert_host',
	TARGET: 'target'
} as const;
export type NewKindKey = (typeof NewKind)[keyof typeof NewKind];

export const KIND_ORDER: NewKindKey[] = Object.values(NewKind);

export const KIND_LABELS: Record<NewKindKey, string> = {
	[NewKind.FINDING]: 'Findings',
	[NewKind.PROGRAM]: 'Programs',
	[NewKind.SCOPE]: 'In scope',
	[NewKind.OUT_OF_SCOPE]: 'Out of scope',
	[NewKind.BOUNTY_TABLE]: 'Bounty table',
	[NewKind.RULES]: 'Rules',
	[NewKind.CERT_HOST]: 'Certificate hosts',
	[NewKind.TARGET]: 'Targets'
};

export const KIND_NOUN: Record<NewKindKey, [string, string]> = {
	[NewKind.FINDING]: ['finding', 'findings'],
	[NewKind.PROGRAM]: ['program', 'programs'],
	[NewKind.SCOPE]: ['asset in scope', 'assets in scope'],
	[NewKind.OUT_OF_SCOPE]: ['asset out of scope', 'assets out of scope'],
	[NewKind.BOUNTY_TABLE]: ['bounty change', 'bounty changes'],
	[NewKind.RULES]: ['rule change', 'rule changes'],
	[NewKind.CERT_HOST]: ['certificate host', 'certificate hosts'],
	[NewKind.TARGET]: ['target', 'targets']
};

export const SCAN_KINDS: ReadonlySet<string> = new Set([NewKind.FINDING]);
export const BOUNTY_KINDS: ReadonlySet<string> = new Set(
	KIND_ORDER.filter((k) => !SCAN_KINDS.has(k))
);
export const TERMS_KINDS: ReadonlySet<string> = new Set([NewKind.BOUNTY_TABLE, NewKind.RULES]);
export const GONE_KINDS: ReadonlySet<string> = new Set([NewKind.OUT_OF_SCOPE]);
export const SELECTABLE_KINDS: ReadonlySet<string> = new Set([
	NewKind.SCOPE,
	NewKind.CERT_HOST,
	NewKind.TARGET
]);

export const KIND_DIMENSION: Partial<Record<NewKindKey, SurfaceDimension>> = {
	[NewKind.FINDING]: SurfaceDimension.VULNERABILITIES
};

export const ALERT_SEVERITIES: string[] = [Severity.CRITICAL, Severity.HIGH];
export const NEW_FINDINGS_QUERY = `is:new (${ALERT_SEVERITIES.map((s) => `severity:${s}`).join(' OR ')})`;

export const NewBasis = { MARK: 'mark', WINDOW: 'window', DAYS: 'days' } as const;

export const SubjectKind = {
	RUN: 'run',
	PROGRAM: 'program',
	LIBRARY: 'library',
	TARGETS: 'targets'
} as const;

export const ProgramRing = { ENGAGED: 'engaged', LIBRARY: 'library' } as const;
export type ProgramRingKey = (typeof ProgramRing)[keyof typeof ProgramRing];
export const RING_LABELS: Record<ProgramRingKey, string> = {
	[ProgramRing.ENGAGED]: 'Programs with my targets',
	[ProgramRing.LIBRARY]: 'Every program'
};

export const Fact = {
	CRITICAL: 'critical',
	HIGH: 'high',
	KEV: 'kev',
	NOT_TARGET: 'not_target',
	ANSWERING: 'answering',
	NOT_SCANNED: 'not_scanned'
} as const;

export const NEW_WINDOWS = [
	{ key: 'since', label: 'Since caught up' },
	{ key: '24h', label: '24h' },
	{ key: '7d', label: '7d' },
	{ key: '30d', label: '30d' }
] as const;
export type NewWindowKey = (typeof NEW_WINDOWS)[number]['key'];
export const SINCE_KEY: NewWindowKey = 'since';

export const NewSource = { ALL: 'all', TARGETS: 'targets', BOUNTY: 'bounty' } as const;
export type NewSourceKey = (typeof NewSource)[keyof typeof NewSource];
export const SOURCE_OPTIONS: { key: NewSourceKey; label: string }[] = [
	{ key: NewSource.ALL, label: 'All' },
	{ key: NewSource.TARGETS, label: 'My targets' },
	{ key: NewSource.BOUNTY, label: 'Bounty Hub' }
];
export const SOURCE_KINDS: Record<NewSourceKey, ReadonlySet<string>> = {
	[NewSource.ALL]: new Set(KIND_ORDER),
	[NewSource.TARGETS]: SCAN_KINDS,
	[NewSource.BOUNTY]: BOUNTY_KINDS
};

export const NewTab = { TIMELINE: 'timeline', VISUAL: 'visual' } as const;
export type NewTabKey = (typeof NewTab)[keyof typeof NewTab];
export const NEW_TABS: { key: NewTabKey; label: string }[] = [
	{ key: NewTab.TIMELINE, label: 'Timeline' },
	{ key: NewTab.VISUAL, label: 'Visual changes' }
];

export const RUN_VERBS: Partial<Record<ScanStatus, string>> = {
	completed: 'finished',
	cancelled: 'cancelled',
	failed: 'failed',
	running: 'running',
	paused: 'paused',
	pending: 'queued'
};

export const Signal = {
	CRITICAL: 'critical',
	HIGH: 'high'
} as const;
export type SignalKey = (typeof Signal)[keyof typeof Signal] | NewKindKey;
export const SIGNAL_LABELS: Record<string, string> = {
	[Signal.CRITICAL]: 'Critical findings',
	[Signal.HIGH]: 'High findings',
	...KIND_LABELS
};

export const VISUAL_FIELD_LABELS: Record<string, string> = {
	http_status: 'Status',
	page_title: 'Title',
	tech: 'Technology',
	webserver: 'Server'
};
export const VISUAL_MAX_DISTANCE = 64;

export const NEW_KEYS: [string, string][] = [
	['j / k', 'Move between events'],
	['Enter or o', 'Expand or collapse the event'],
	['g', 'Go to the run or program'],
	['s', 'Scan the target'],
	['1 2', 'Switch tab'],
	['/', 'Filter'],
	['Esc', 'Collapse or clear selection']
];

export const VISUAL_KEYS: [string, string][] = [
	['j / k', 'Move between changes'],
	['Enter', 'Compare the captures'],
	['s', 'Scan the target']
];
