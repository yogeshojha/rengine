import CalendarClock from '@lucide/svelte/icons/calendar-clock';
import KeyRound from '@lucide/svelte/icons/key-round';
import type { BadgeVariant } from '$lib/components/ui/badge';
import type { IconComponent } from '$lib/config/icons';
import { SURFACE, SurfaceDimension, type SurfaceSpec } from '$lib/config/surface';

// mirrors shared/definitions/tripwires.py
export enum TripwireTrigger {
	ScanSettled = 'scan_settled',
	ScanLive = 'scan_live',
	Daily = 'daily'
}

export enum TripwireSource {
	LeakedLogins = 'leaked_logins'
}

export enum FireOn {
	Appears = 'appears',
	BecomesTrue = 'becomes_true',
	Matches = 'matches'
}

export enum ScopeKind {
	All = 'all',
	Targets = 'targets',
	Organization = 'organization',
	Tag = 'tag'
}

export enum ActionKind {
	Notify = 'notify',
	Scan = 'scan'
}

export enum CheckStatus {
	Fired = 'fired',
	Quiet = 'quiet',
	NoBaseline = 'no_baseline',
	NotCovered = 'not_covered',
	Error = 'error'
}

export enum OutcomeStatus {
	Done = 'done',
	Skipped = 'skipped',
	Failed = 'failed'
}

export const MAX_NAME = 80;
export const MAX_RUNS_PER_DAY = 5;
export const RECENT_DAYS = 30;

export const TRIGGER_LABELS: Record<TripwireTrigger, string> = {
	[TripwireTrigger.ScanSettled]: 'After a scan',
	[TripwireTrigger.ScanLive]: 'During a scan',
	[TripwireTrigger.Daily]: 'Daily'
};

export const FIRE_ON_LABELS: Record<FireOn, string> = {
	[FireOn.Appears]: 'Appears',
	[FireOn.BecomesTrue]: 'Becomes true',
	[FireOn.Matches]: 'Matches'
};

export const FIRE_ON_VERB: Record<FireOn, string> = {
	[FireOn.Appears]: 'appeared',
	[FireOn.BecomesTrue]: 'started matching',
	[FireOn.Matches]: 'matched'
};

export const FIRE_ON_CLAUSE: Record<FireOn, string> = {
	[FireOn.Appears]: 'appears',
	[FireOn.BecomesTrue]: 'starts matching',
	[FireOn.Matches]: 'matches'
};

export const SCOPE_LABELS: Record<ScopeKind, string> = {
	[ScopeKind.All]: 'All targets',
	[ScopeKind.Targets]: 'Targets',
	[ScopeKind.Organization]: 'Organization',
	[ScopeKind.Tag]: 'Tag'
};

export const ACTION_LABELS: Record<ActionKind, string> = {
	[ActionKind.Notify]: 'Notify',
	[ActionKind.Scan]: 'Focused scan'
};

export const CHECK_STATUS_LABELS: Record<CheckStatus, string> = {
	[CheckStatus.Fired]: 'Fired',
	[CheckStatus.Quiet]: 'Not fired',
	[CheckStatus.NoBaseline]: 'First scan',
	[CheckStatus.NotCovered]: 'Not scanned',
	[CheckStatus.Error]: 'Error'
};

export const CHECK_STATUS_VARIANT: Record<CheckStatus, BadgeVariant> = {
	[CheckStatus.Fired]: 'info',
	[CheckStatus.Quiet]: 'outline',
	[CheckStatus.NoBaseline]: 'outline',
	[CheckStatus.NotCovered]: 'outline',
	[CheckStatus.Error]: 'destructive'
};

export const SOURCE_ICONS: Record<TripwireSource, IconComponent> = {
	[TripwireSource.LeakedLogins]: KeyRound
};

/** Where a daily check's target page shows what the source read. */
export const SOURCE_PAGE: Record<TripwireSource, { tab: string; label: string }> = {
	[TripwireSource.LeakedLogins]: { tab: 'infostealer', label: 'Open infostealer report' }
};

export function sourcePage(source: string | null | undefined) {
	return SOURCE_PAGE[source as TripwireSource] ?? null;
}

export function isDaily(trigger: string): boolean {
	return trigger === TripwireTrigger.Daily;
}

export function sourceIcon(source: string | null | undefined): IconComponent {
	return SOURCE_ICONS[source as TripwireSource] ?? CalendarClock;
}

export const RUN_PARAM = 'run';
export const TRIPWIRE_PARAM = 'tripwire';

export function checkStatusLabel(status: string): string {
	return CHECK_STATUS_LABELS[status as CheckStatus] ?? status;
}

export function fireOnLabel(value: string): string {
	return FIRE_ON_LABELS[value as FireOn] ?? value;
}

export function triggerLabel(value: string): string {
	return TRIGGER_LABELS[value as TripwireTrigger] ?? value;
}

export function actionLabel(value: string): string {
	return ACTION_LABELS[value as ActionKind] ?? value;
}

export function dimensionSpec(key: string): SurfaceSpec {
	return SURFACE[key as SurfaceDimension] ?? SURFACE[SurfaceDimension.WEB_ASSETS];
}
