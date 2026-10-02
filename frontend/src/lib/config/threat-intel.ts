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
import type { BadgeVariant } from '$lib/components/ui/badge';
import type { IconComponent } from './icons';

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

export const SIGNAL_LABELS: Record<string, string> = {
	[ExploitSignal.KEV]: 'Known exploited',
	[ExploitSignal.RANSOM_PATH]: 'Ransomware path',
	[ExploitSignal.RANSOMWARE]: 'Used by ransomware',
	[ExploitSignal.FRESH_EXPLOIT]: 'Exploit published after the scan',
	[ExploitSignal.OVERDUE]: 'Past the CISA deadline',
	[ExploitSignal.WEAPONISED]: 'Public exploit available',
	[ExploitSignal.LIKELY]: 'Likely to be exploited',
	[ExploitSignal.REACHABLE]: 'Directly reachable',
	[ExploitSignal.BYPASSED]: 'Matched through a WAF',
	[ExploitSignal.CROWD]: 'Widely deployed software',
	[ExploitSignal.UNTESTABLE]: 'No scanner template'
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

export enum SignalTone {
	CRITICAL = 'critical',
	WARNING = 'warning',
	INFO = 'info',
	NEUTRAL = 'neutral'
}

export const SIGNAL_TONE: Record<string, SignalTone> = {
	[ExploitSignal.KEV]: SignalTone.CRITICAL,
	[ExploitSignal.RANSOM_PATH]: SignalTone.CRITICAL,
	[ExploitSignal.RANSOMWARE]: SignalTone.CRITICAL,
	[ExploitSignal.FRESH_EXPLOIT]: SignalTone.CRITICAL,
	[ExploitSignal.OVERDUE]: SignalTone.WARNING,
	[ExploitSignal.WEAPONISED]: SignalTone.WARNING,
	[ExploitSignal.LIKELY]: SignalTone.WARNING,
	[ExploitSignal.REACHABLE]: SignalTone.WARNING,
	[ExploitSignal.BYPASSED]: SignalTone.WARNING,
	[ExploitSignal.CROWD]: SignalTone.INFO,
	[ExploitSignal.UNTESTABLE]: SignalTone.INFO
};

export const TONE_BADGE: Record<SignalTone, BadgeVariant> = {
	[SignalTone.CRITICAL]: 'destructive',
	[SignalTone.WARNING]: 'warning',
	[SignalTone.INFO]: 'info',
	[SignalTone.NEUTRAL]: 'secondary'
};

/** The badge variant for an exploit signal. */
export function signalVariant(kind: string): BadgeVariant {
	return TONE_BADGE[SIGNAL_TONE[kind] ?? SignalTone.NEUTRAL];
}

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

export const BAND_FILL: Record<string, string> = {
	[ExploitBand.VERY_LIKELY]: 'var(--destructive)',
	[ExploitBand.LIKELY]: 'var(--sev-high)',
	[ExploitBand.POSSIBLE]: 'var(--warning)',
	[ExploitBand.UNLIKELY]: 'var(--muted-foreground)'
};

export const MAX_EXPLOIT_SCORE = 100;

export function exploitTone(score: number): string {
	if (score >= 80) return 'var(--destructive)';
	if (score >= 50) return 'var(--sev-high)';
	if (score >= 20) return 'var(--warning)';
	return 'var(--muted-foreground)';
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
	return `above ${Math.floor(pct * 100)}% of CVEs`;
}

export function hostsLabel(hosts: number | null | undefined): string {
	if (!hosts) return '';
	if (hosts >= 1_000_000) return `${(hosts / 1_000_000).toFixed(1)}M`;
	if (hosts >= 1_000) return `${Math.round(hosts / 1_000)}k`;
	return String(hosts);
}
