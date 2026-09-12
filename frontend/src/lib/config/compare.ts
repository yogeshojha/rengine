import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import Flame from '@lucide/svelte/icons/flame';
import Plug from '@lucide/svelte/icons/plug';
import LockOpen from '@lucide/svelte/icons/lock-open';
import Bug from '@lucide/svelte/icons/bug';
import TrendingUp from '@lucide/svelte/icons/trending-up';
import FileBadge from '@lucide/svelte/icons/file-badge';
import ShieldOff from '@lucide/svelte/icons/shield-off';
import Eye from '@lucide/svelte/icons/eye';
import Move from '@lucide/svelte/icons/move';
import Power from '@lucide/svelte/icons/power';
import CloudOff from '@lucide/svelte/icons/cloud-off';
import DoorOpen from '@lucide/svelte/icons/door-open';
import FileDiff from '@lucide/svelte/icons/file-diff';
import Globe from '@lucide/svelte/icons/globe';
import Network from '@lucide/svelte/icons/network';
import Waypoints from '@lucide/svelte/icons/waypoints';
import PencilLine from '@lucide/svelte/icons/pencil-line';
import CircleMinus from '@lucide/svelte/icons/circle-minus';
import DoorClosed from '@lucide/svelte/icons/door-closed';
import type { IconComponent } from './icons';
import {
	CHANGE_VERB,
	COMPARABILITY,
	type ChangeVerb,
	type Comparability
} from '$lib/types/compare';

export const COMPARE_TAB_ALL = 'all';

export const COMPARE_MODES = ['ledger', 'diff'] as const;
export type CompareMode = (typeof COMPARE_MODES)[number];
export const COMPARE_DIGEST_SIZE = 50;
export const COMPARE_PAGE_SIZE = 50;

export interface VerbSpec {
	key: ChangeVerb;
	label: string;
	rail: string;
	dot: string;
}

export const VERB: Record<ChangeVerb, VerbSpec> = {
	[CHANGE_VERB.APPEARED]: {
		key: CHANGE_VERB.APPEARED,
		label: 'Appeared',
		rail: 'bg-primary',
		dot: 'bg-primary'
	},
	[CHANGE_VERB.CHANGED]: {
		key: CHANGE_VERB.CHANGED,
		label: 'Changed',
		rail: 'bg-info',
		dot: 'bg-info'
	},
	[CHANGE_VERB.DISAPPEARED]: {
		key: CHANGE_VERB.DISAPPEARED,
		label: 'Disappeared',
		rail: 'bg-transparent ring-1 ring-inset ring-muted-foreground/50',
		dot: 'bg-transparent ring-1 ring-inset ring-muted-foreground/50'
	},
	[CHANGE_VERB.UNCONFIRMED]: {
		key: CHANGE_VERB.UNCONFIRMED,
		label: 'Unconfirmed',
		rail: 'bg-warning/60',
		dot: 'bg-warning/60'
	},
	[CHANGE_VERB.UNCHANGED]: {
		key: CHANGE_VERB.UNCHANGED,
		label: 'Unchanged',
		rail: 'bg-border',
		dot: 'bg-border'
	}
};

export const COMPARABILITY_LABEL: Record<Comparability, string> = {
	[COMPARABILITY.LIKE_FOR_LIKE]: 'Comparable',
	[COMPARABILITY.SETTINGS_DIFFER]: 'Settings differ',
	[COMPARABILITY.QUALITY_DIFFERS]: 'Runs differ in depth',
	[COMPARABILITY.NOT_COVERED]: 'Not scanned'
};

export const COMPARABILITY_TONE: Record<Comparability, 'success' | 'warning' | 'muted'> = {
	[COMPARABILITY.LIKE_FOR_LIKE]: 'success',
	[COMPARABILITY.SETTINGS_DIFFER]: 'warning',
	[COMPARABILITY.QUALITY_DIFFERS]: 'warning',
	[COMPARABILITY.NOT_COVERED]: 'muted'
};

export interface SignalSpec {
	label: string;
	icon: IconComponent;
	tone: 'critical' | 'warning' | 'notice' | 'quiet';
}

export const SIGNAL: Record<string, SignalSpec> = {
	kev_appeared: { label: 'Exploited in the wild', icon: Flame, tone: 'critical' },
	critical_appeared: { label: 'High severity finding', icon: ShieldAlert, tone: 'critical' },
	finding_appeared: { label: 'New finding', icon: Bug, tone: 'warning' },
	severity_raised: { label: 'Severity raised', icon: TrendingUp, tone: 'warning' },
	sensitive_service_opened: { label: 'Sensitive service opened', icon: Plug, tone: 'critical' },
	auth_dropped: { label: 'Authentication dropped', icon: LockOpen, tone: 'critical' },
	service_opened: { label: 'Service opened', icon: DoorOpen, tone: 'notice' },
	cert_expired: { label: 'Certificate expired', icon: FileBadge, tone: 'warning' },
	waf_gone: { label: 'WAF no longer answering', icon: ShieldOff, tone: 'warning' },
	cdn_gone: { label: 'No longer behind a CDN', icon: CloudOff, tone: 'notice' },
	hosting_moved: { label: 'Hosting moved', icon: Move, tone: 'notice' },
	host_woke: { label: 'Host started responding', icon: Power, tone: 'notice' },
	body_changed: { label: 'Response body changed', icon: FileDiff, tone: 'notice' },
	exposed_host_appeared: { label: 'New exposed host', icon: Eye, tone: 'warning' },
	host_appeared: { label: 'New host', icon: Globe, tone: 'notice' },
	address_appeared: { label: 'New address', icon: Network, tone: 'notice' },
	endpoint_appeared: { label: 'New endpoint', icon: Waypoints, tone: 'notice' },
	attributes_changed: { label: 'Details changed', icon: PencilLine, tone: 'quiet' },
	finding_gone: { label: 'Finding gone', icon: CircleMinus, tone: 'quiet' },
	service_closed: { label: 'Service closed', icon: DoorClosed, tone: 'quiet' },
	host_gone: { label: 'Host gone', icon: CircleMinus, tone: 'quiet' },
	asset_gone: { label: 'Gone', icon: CircleMinus, tone: 'quiet' }
};

export const SIGNAL_TONE_CLASS: Record<SignalSpec['tone'], string> = {
	critical: 'text-destructive',
	warning: 'text-warning',
	notice: 'text-info',
	quiet: 'text-muted-foreground'
};

export function signalSpec(key: string): SignalSpec {
	return SIGNAL[key] ?? SIGNAL.attributes_changed;
}

/** Mirrors shared/definitions/compare.py:REFUSAL_REASON. */
export const REFUSAL = {
	DIFFERENT_TARGET: 'Both runs must cover the same target.',
	UNFINISHED: 'This run has not finished.',
	FOCUSED_AGAINST_FULL: 'A focused run is compared with its parent run only. Open the focused run.',
	FULL_AGAINST_FOCUSED: 'A full run cannot be compared with a focused run. Select two full runs.',
	SAME_RUN: 'Pick two different runs.',
	NO_EARLIER_RUN: 'No earlier run of this target to compare with.',
	NEED_ONE_MORE: 'Select one more run of the same target.',
	TOO_MANY: 'Select exactly two runs.'
} as const;

/** Banner order. */
export const RUN_FACET_ORDER = [
	'engine',
	'context',
	'auth',
	'intensity',
	'proxy',
	'included_subdomains',
	'excluded_subdomains',
	'excluded_paths',
	'excluded_ips',
	'http_protocol',
	'crawl',
	'headers',
	'schedule'
] as const;

export function facetRank(key: string): number {
	const i = (RUN_FACET_ORDER as readonly string[]).indexOf(key);
	return i === -1 ? RUN_FACET_ORDER.length : i;
}
