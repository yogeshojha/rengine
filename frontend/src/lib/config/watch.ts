import BellIcon from '@lucide/svelte/icons/bell';
import CalendarClockIcon from '@lucide/svelte/icons/calendar-clock';
import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
import EyeIcon from '@lucide/svelte/icons/eye';
import MinusIcon from '@lucide/svelte/icons/minus';
import PauseIcon from '@lucide/svelte/icons/pause';
import PlayIcon from '@lucide/svelte/icons/play';
import PlusIcon from '@lucide/svelte/icons/plus';
import SettingsIcon from '@lucide/svelte/icons/settings-2';
import ShieldBanIcon from '@lucide/svelte/icons/shield-ban';

import type { IconComponent } from '$lib/config/icons';
import type { BadgeVariant } from '$lib/components/ui/badge';
import {
	WatchCadence,
	WatchEventKind,
	WatchHostState,
	type WatchHostFilter
} from '$lib/types/watch';

export const CADENCE_LABELS: Record<WatchCadence, string> = {
	[WatchCadence.Off]: 'Off',
	[WatchCadence.Daily]: 'Daily',
	[WatchCadence.Weekly]: 'Weekly',
	[WatchCadence.Monthly]: 'Monthly'
};

export const CADENCES: readonly WatchCadence[] = [
	WatchCadence.Off,
	WatchCadence.Daily,
	WatchCadence.Weekly,
	WatchCadence.Monthly
] as const;

export const HOST_STATE_VARIANT: Record<WatchHostState, BadgeVariant> = {
	[WatchHostState.New]: 'secondary',
	[WatchHostState.Unresolved]: 'secondary',
	[WatchHostState.Known]: 'outline',
	[WatchHostState.OutOfScope]: 'outline',
	[WatchHostState.Probing]: 'info',
	[WatchHostState.Quiet]: 'outline',
	[WatchHostState.Alerted]: 'default',
	[WatchHostState.Muted]: 'secondary'
};

export const HOST_FILTERS: { key: WatchHostFilter; label: string }[] = [
	{ key: 'all', label: 'All' },
	{ key: 'arrived', label: 'Arrived' },
	{ key: 'alerted', label: 'Alerted' },
	{ key: 'unresolved', label: 'Unresolved' },
	{ key: 'out_of_scope', label: 'Out of scope' }
];

export const EVENT_ICONS: Record<WatchEventKind, IconComponent> = {
	[WatchEventKind.WatchStarted]: EyeIcon,
	[WatchEventKind.WatchPaused]: PauseIcon,
	[WatchEventKind.WatchResumed]: PlayIcon,
	[WatchEventKind.WatchUpdated]: SettingsIcon,
	[WatchEventKind.BaselineQueued]: CalendarClockIcon,
	[WatchEventKind.ScopeAdded]: PlusIcon,
	[WatchEventKind.ScopeRemoved]: MinusIcon,
	[WatchEventKind.HostAlerted]: BellIcon,
	[WatchEventKind.HostOutOfScope]: ShieldBanIcon,
	[WatchEventKind.StreamError]: CircleAlertIcon
};

export const EVENT_TONE_CLASS: Partial<Record<WatchEventKind, string>> = {
	[WatchEventKind.HostAlerted]: 'text-primary',
	[WatchEventKind.ScopeRemoved]: 'text-warning',
	[WatchEventKind.StreamError]: 'text-destructive',
	[WatchEventKind.WatchPaused]: 'text-muted-foreground'
};

export const DEFAULT_RATE_LIMIT = 5;
export const MAX_RATE_LIMIT = 1000;
export const WATCH_HOST_PAGE_SIZE = 50;
export const WATCH_EVENT_PAGE_SIZE = 50;
export const STREAM_POLL_MS = 30_000;
export const ALERT_QUERY_EXAMPLES = ['is:live', 'status:200 and not title:parked', 'tech:*'];
