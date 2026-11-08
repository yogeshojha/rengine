import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import Flame from '@lucide/svelte/icons/flame';
import Plug from '@lucide/svelte/icons/plug';
import LockOpen from '@lucide/svelte/icons/lock-open';
import Bug from '@lucide/svelte/icons/bug';
import TrendingUp from '@lucide/svelte/icons/trending-up';
import FileBadge from '@lucide/svelte/icons/file-badge';
import MailWarning from '@lucide/svelte/icons/mail-warning';
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
}

export const VERB: Record<ChangeVerb, VerbSpec> = {
	[CHANGE_VERB.APPEARED]: { key: CHANGE_VERB.APPEARED, label: 'Appeared' },
	[CHANGE_VERB.CHANGED]: { key: CHANGE_VERB.CHANGED, label: 'Changed' },
	[CHANGE_VERB.DISAPPEARED]: { key: CHANGE_VERB.DISAPPEARED, label: 'Disappeared' },
	[CHANGE_VERB.UNCONFIRMED]: { key: CHANGE_VERB.UNCONFIRMED, label: 'Unconfirmed' },
	[CHANGE_VERB.UNCHANGED]: { key: CHANGE_VERB.UNCHANGED, label: 'Unchanged' }
};

export const COMPARABILITY_LABEL: Record<Comparability, string> = {
	[COMPARABILITY.LIKE_FOR_LIKE]: 'Comparable',
	[COMPARABILITY.SETTINGS_DIFFER]: 'Settings differ',
	[COMPARABILITY.QUALITY_DIFFERS]: 'Runs differ in depth',
	[COMPARABILITY.NOT_COVERED]: 'Coverage differs'
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

// mirrors shared/definitions/compare.py:ChangeSignal
export enum ChangeSignal {
	KEV_APPEARED = 'kev_appeared',
	CRITICAL_APPEARED = 'critical_appeared',
	FINDING_APPEARED = 'finding_appeared',
	SEVERITY_RAISED = 'severity_raised',
	SENSITIVE_SERVICE_OPENED = 'sensitive_service_opened',
	AUTH_DROPPED = 'auth_dropped',
	SERVICE_OPENED = 'service_opened',
	CERT_EXPIRED = 'cert_expired',
	POSTURE_WEAKENED = 'posture_weakened',
	WAF_GONE = 'waf_gone',
	CDN_GONE = 'cdn_gone',
	HOSTING_MOVED = 'hosting_moved',
	HOST_WOKE = 'host_woke',
	BODY_CHANGED = 'body_changed',
	EXPOSED_HOST_APPEARED = 'exposed_host_appeared',
	HOST_APPEARED = 'host_appeared',
	ADDRESS_APPEARED = 'address_appeared',
	ENDPOINT_APPEARED = 'endpoint_appeared',
	ATTRIBUTES_CHANGED = 'attributes_changed',
	FINDING_GONE = 'finding_gone',
	SERVICE_CLOSED = 'service_closed',
	HOST_GONE = 'host_gone',
	ASSET_GONE = 'asset_gone'
}

export const SIGNAL: Record<string, SignalSpec> = {
	[ChangeSignal.KEV_APPEARED]: { label: 'Known exploited finding', icon: Flame, tone: 'critical' },
	[ChangeSignal.CRITICAL_APPEARED]: {
		label: 'Critical or high finding',
		icon: ShieldAlert,
		tone: 'critical'
	},
	[ChangeSignal.FINDING_APPEARED]: { label: 'New finding', icon: Bug, tone: 'warning' },
	[ChangeSignal.SEVERITY_RAISED]: { label: 'Severity raised', icon: TrendingUp, tone: 'warning' },
	[ChangeSignal.SENSITIVE_SERVICE_OPENED]: {
		label: 'Sensitive service opened',
		icon: Plug,
		tone: 'critical'
	},
	[ChangeSignal.AUTH_DROPPED]: {
		label: 'Authentication dropped',
		icon: LockOpen,
		tone: 'critical'
	},
	[ChangeSignal.SERVICE_OPENED]: { label: 'Service opened', icon: DoorOpen, tone: 'notice' },
	[ChangeSignal.CERT_EXPIRED]: { label: 'Certificate expired', icon: FileBadge, tone: 'warning' },
	[ChangeSignal.POSTURE_WEAKENED]: {
		label: 'Sender policy weakened',
		icon: MailWarning,
		tone: 'warning'
	},
	[ChangeSignal.WAF_GONE]: { label: 'WAF no longer detected', icon: ShieldOff, tone: 'warning' },
	[ChangeSignal.CDN_GONE]: { label: 'No longer behind a CDN', icon: CloudOff, tone: 'notice' },
	[ChangeSignal.HOSTING_MOVED]: { label: 'Hosting moved', icon: Move, tone: 'notice' },
	[ChangeSignal.HOST_WOKE]: { label: 'Web asset started responding', icon: Power, tone: 'notice' },
	[ChangeSignal.BODY_CHANGED]: { label: 'Response body changed', icon: FileDiff, tone: 'notice' },
	[ChangeSignal.EXPOSED_HOST_APPEARED]: {
		label: 'New exposed web asset',
		icon: Eye,
		tone: 'warning'
	},
	[ChangeSignal.HOST_APPEARED]: { label: 'New web asset', icon: Globe, tone: 'notice' },
	[ChangeSignal.ADDRESS_APPEARED]: { label: 'New address', icon: Network, tone: 'notice' },
	[ChangeSignal.ENDPOINT_APPEARED]: { label: 'New endpoint', icon: Waypoints, tone: 'notice' },
	[ChangeSignal.ATTRIBUTES_CHANGED]: { label: 'Details changed', icon: PencilLine, tone: 'quiet' },
	[ChangeSignal.FINDING_GONE]: { label: 'Finding gone', icon: CircleMinus, tone: 'quiet' },
	[ChangeSignal.SERVICE_CLOSED]: { label: 'Service closed', icon: DoorClosed, tone: 'quiet' },
	[ChangeSignal.HOST_GONE]: { label: 'Web asset gone', icon: CircleMinus, tone: 'quiet' },
	[ChangeSignal.ASSET_GONE]: { label: 'Gone', icon: CircleMinus, tone: 'quiet' }
};

export const SIGNAL_TONE_CLASS: Record<SignalSpec['tone'], string> = {
	critical: 'text-destructive',
	warning: 'text-warning',
	notice: 'text-info',
	quiet: 'text-muted-foreground'
};

export function signalSpec(key: string): SignalSpec {
	return SIGNAL[key] ?? SIGNAL[ChangeSignal.ATTRIBUTES_CHANGED];
}

/** Mirrors shared/definitions/compare.py:REFUSAL_REASON. */
export const REFUSAL = {
	DIFFERENT_TARGET: 'Both runs must cover the same target.',
	UNFINISHED: 'This run has not finished.',
	FOCUSED_AGAINST_FULL: 'A focused run is compared with its parent run only. Open the focused run.',
	FULL_AGAINST_FOCUSED: 'A full run cannot be compared with a focused run. Select two full runs.',
	SAME_RUN: 'Select two different runs.',
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
	'seed_assets',
	'excluded_subdomains',
	'excluded_paths',
	'excluded_ips',
	'http_protocol',
	'headers',
	'schedule',
	'rate_ceiling',
	'thread_multiplier',
	'timeout_multiplier'
] as const;

export function facetRank(key: string): number {
	const i = (RUN_FACET_ORDER as readonly string[]).indexOf(key);
	return i === -1 ? RUN_FACET_ORDER.length : i;
}
