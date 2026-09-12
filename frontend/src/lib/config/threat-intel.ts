import Biohazard from '@lucide/svelte/icons/biohazard';
import CalendarX from '@lucide/svelte/icons/calendar-x';
import EyeOff from '@lucide/svelte/icons/eye-off';
import Flame from '@lucide/svelte/icons/flame';
import Globe from '@lucide/svelte/icons/globe';
import Radiation from '@lucide/svelte/icons/radiation';
import Swords from '@lucide/svelte/icons/swords';
import TrendingUp from '@lucide/svelte/icons/trending-up';
import ShieldOff from '@lucide/svelte/icons/shield-off';
import Unplug from '@lucide/svelte/icons/unplug';
import Zap from '@lucide/svelte/icons/zap';
import type { IconComponent } from './icons';

// mirrors shared/definitions/threat_intel.py
export enum FeedKind {
	EPSS = 'epss',
	KEV = 'kev'
}

export enum FeedStatus {
	EMPTY = 'empty',
	READY = 'ready',
	STALE = 'stale',
	FAILED = 'failed',
	SYNCING = 'syncing'
}

export const FEED_STATUS_TONE: Record<string, string> = {
	[FeedStatus.READY]: 'text-success',
	[FeedStatus.STALE]: 'text-warning',
	[FeedStatus.FAILED]: 'text-destructive',
	[FeedStatus.SYNCING]: 'text-info',
	[FeedStatus.EMPTY]: 'text-muted-foreground'
};

export const FEED_STATUS_DOT: Record<string, string> = {
	[FeedStatus.READY]: 'bg-success',
	[FeedStatus.STALE]: 'bg-warning',
	[FeedStatus.FAILED]: 'bg-destructive',
	[FeedStatus.SYNCING]: 'bg-info',
	[FeedStatus.EMPTY]: 'bg-muted-foreground'
};

export enum ExploitSignal {
	KEV = 'kev',
	RANSOM_PATH = 'ransom_path',
	RANSOMWARE = 'ransomware',
	FRESH_EXPLOIT = 'fresh_exploit',
	OVERDUE = 'overdue',
	WEAPONISED = 'weaponised',
	LIKELY = 'likely',
	REACHABLE = 'reachable',
	BYPASSED = 'bypassed',
	CROWD = 'crowd',
	UNTESTABLE = 'untestable'
}

export const SIGNAL_ORDER: string[] = [
	ExploitSignal.KEV,
	ExploitSignal.RANSOM_PATH,
	ExploitSignal.RANSOMWARE,
	ExploitSignal.FRESH_EXPLOIT,
	ExploitSignal.OVERDUE,
	ExploitSignal.WEAPONISED,
	ExploitSignal.LIKELY,
	ExploitSignal.REACHABLE,
	ExploitSignal.BYPASSED,
	ExploitSignal.CROWD,
	ExploitSignal.UNTESTABLE
];

export const SIGNAL_LABELS: Record<string, string> = {
	[ExploitSignal.KEV]: 'Known exploited',
	[ExploitSignal.RANSOM_PATH]: 'Ransomware path',
	[ExploitSignal.RANSOMWARE]: 'Used by ransomware',
	[ExploitSignal.FRESH_EXPLOIT]: 'Exploit published since the last scan',
	[ExploitSignal.OVERDUE]: 'Past the CISA deadline',
	[ExploitSignal.WEAPONISED]: 'Public exploit available',
	[ExploitSignal.LIKELY]: 'Likely to be exploited',
	[ExploitSignal.REACHABLE]: 'Directly reachable',
	[ExploitSignal.BYPASSED]: 'Confirmed through a WAF',
	[ExploitSignal.CROWD]: 'Mass-scanned software',
	[ExploitSignal.UNTESTABLE]: 'No check exists'
};

export const SIGNAL_HELP: Record<string, string> = {
	[ExploitSignal.KEV]: 'CISA lists these CVEs as exploited in the wild.',
	[ExploitSignal.RANSOM_PATH]:
		'Used in ransomware campaigns. The same host exposes a sensitive service.',
	[ExploitSignal.RANSOMWARE]: 'CISA records these CVEs in known ransomware campaigns.',
	[ExploitSignal.FRESH_EXPLOIT]: 'A public exploit was published after the scan that found these.',
	[ExploitSignal.OVERDUE]: 'The federal remediation deadline for these CVEs has passed.',
	[ExploitSignal.WEAPONISED]: 'Working exploit code is published for these.',
	[ExploitSignal.LIKELY]: 'EPSS 8.8% or above.',
	[ExploitSignal.REACHABLE]:
		'The host answers from the internet with no CDN or WAF in front of it.',
	[ExploitSignal.BYPASSED]: 'A WAF or CDN sits in front of the host and the check succeeded.',
	[ExploitSignal.CROWD]: 'Hundreds of thousands of hosts run this software.',
	[ExploitSignal.UNTESTABLE]: 'No scanner template covers these.'
};

export const SIGNAL_ICONS: Record<string, IconComponent> = {
	[ExploitSignal.KEV]: Flame,
	[ExploitSignal.RANSOM_PATH]: Biohazard,
	[ExploitSignal.RANSOMWARE]: Radiation,
	[ExploitSignal.FRESH_EXPLOIT]: TrendingUp,
	[ExploitSignal.OVERDUE]: CalendarX,
	[ExploitSignal.WEAPONISED]: Swords,
	[ExploitSignal.LIKELY]: Zap,
	[ExploitSignal.REACHABLE]: Unplug,
	[ExploitSignal.BYPASSED]: ShieldOff,
	[ExploitSignal.CROWD]: Globe,
	[ExploitSignal.UNTESTABLE]: EyeOff
};

export const SIGNAL_QUERY: Record<string, string> = {
	[ExploitSignal.KEV]: 'is:kev',
	[ExploitSignal.RANSOM_PATH]: 'signal:ransom_path',
	[ExploitSignal.RANSOMWARE]: 'is:ransomware',
	[ExploitSignal.FRESH_EXPLOIT]: 'signal:fresh_exploit',
	[ExploitSignal.OVERDUE]: 'is:overdue',
	[ExploitSignal.WEAPONISED]: 'is:weaponised',
	[ExploitSignal.LIKELY]: 'signal:likely',
	[ExploitSignal.REACHABLE]: 'signal:reachable',
	[ExploitSignal.BYPASSED]: 'signal:bypassed',
	[ExploitSignal.CROWD]: 'signal:crowd',
	[ExploitSignal.UNTESTABLE]: 'is:untestable'
};

export const TONE_TEXT: Record<string, string> = {
	critical: 'text-destructive',
	warning: 'text-warning',
	info: 'text-info',
	neutral: 'text-muted-foreground'
};

export const TONE_FILL: Record<string, string> = {
	critical: 'var(--destructive)',
	warning: 'var(--warning)',
	info: 'var(--info)',
	neutral: 'var(--muted-foreground)'
};

export enum ExploitBand {
	VERY_LIKELY = 'very_likely',
	LIKELY = 'likely',
	POSSIBLE = 'possible',
	UNLIKELY = 'unlikely'
}

export const BAND_ORDER: string[] = [
	ExploitBand.VERY_LIKELY,
	ExploitBand.LIKELY,
	ExploitBand.POSSIBLE,
	ExploitBand.UNLIKELY
];

export const BAND_LABELS: Record<string, string> = {
	[ExploitBand.VERY_LIKELY]: 'Very likely',
	[ExploitBand.LIKELY]: 'Likely',
	[ExploitBand.POSSIBLE]: 'Possible',
	[ExploitBand.UNLIKELY]: 'Unlikely'
};

export const BAND_HELP: Record<string, string> = {
	[ExploitBand.VERY_LIKELY]: 'EPSS 50% or above.',
	[ExploitBand.LIKELY]: 'EPSS 8.8% or above.',
	[ExploitBand.POSSIBLE]: 'EPSS 1% or above.',
	[ExploitBand.UNLIKELY]: 'EPSS below 1%.'
};

export const BAND_FILL: Record<string, string> = {
	[ExploitBand.VERY_LIKELY]: 'var(--destructive)',
	[ExploitBand.LIKELY]: 'var(--sev-high)',
	[ExploitBand.POSSIBLE]: 'var(--warning)',
	[ExploitBand.UNLIKELY]: 'var(--muted-foreground)'
};

export const MAX_EXPLOIT_SCORE = 100;

export function bandFor(score: number | null | undefined): string | null {
	if (score === null || score === undefined) return null;
	if (score >= 0.5) return ExploitBand.VERY_LIKELY;
	if (score >= 0.088) return ExploitBand.LIKELY;
	if (score >= 0.01) return ExploitBand.POSSIBLE;
	return ExploitBand.UNLIKELY;
}

/** EPSS as a percentage. */
export function epssLabel(score: number | null | undefined): string {
	if (score === null || score === undefined) return '—';
	const pct = score * 100;
	if (pct >= 10) return `${Math.round(pct)}%`;
	if (pct >= 1) return `${pct.toFixed(1)}%`;
	if (pct >= 0.1) return `${pct.toFixed(2)}%`;
	return '<0.1%';
}

export function percentileLabel(pct: number | null | undefined): string {
	if (pct === null || pct === undefined) return '';
	return `worse than ${Math.floor(pct * 100)}% of all CVEs`;
}

export function hostsLabel(hosts: number | null | undefined): string {
	if (!hosts) return '';
	if (hosts >= 1_000_000) return `${(hosts / 1_000_000).toFixed(1)}M`;
	if (hosts >= 1_000) return `${Math.round(hosts / 1_000)}k`;
	return String(hosts);
}
