import AppWindowIcon from '@lucide/svelte/icons/app-window';
import AsteriskIcon from '@lucide/svelte/icons/asterisk';
import BinaryIcon from '@lucide/svelte/icons/binary';
import BrainIcon from '@lucide/svelte/icons/brain';
import BanknoteIcon from '@lucide/svelte/icons/banknote';
import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
import DoorClosedIcon from '@lucide/svelte/icons/door-closed';
import DoorOpenIcon from '@lucide/svelte/icons/door-open';
import MinusIcon from '@lucide/svelte/icons/minus';
import OctagonAlertIcon from '@lucide/svelte/icons/octagon-alert';
import PlusIcon from '@lucide/svelte/icons/plus';
import SparklesIcon from '@lucide/svelte/icons/sparkles';
import CpuIcon from '@lucide/svelte/icons/cpu';
import FileCodeIcon from '@lucide/svelte/icons/file-code';
import FileSignatureIcon from '@lucide/svelte/icons/file-signature';
import GlobeIcon from '@lucide/svelte/icons/globe';
import LinkIcon from '@lucide/svelte/icons/link';
import NetworkIcon from '@lucide/svelte/icons/network';
import ServerIcon from '@lucide/svelte/icons/server';
import ShapesIcon from '@lucide/svelte/icons/shapes';
import SmartphoneIcon from '@lucide/svelte/icons/smartphone';

import type { IconComponent } from '$lib/config/icons';
import { AssetGroup, ProgramState, ScopeState, SubmissionState } from '$lib/types/bounty-program';

export const ASSET_ICONS: Record<string, IconComponent> = {
	globe: GlobeIcon,
	asterisk: AsteriskIcon,
	link: LinkIcon,
	server: ServerIcon,
	network: NetworkIcon,
	shapes: ShapesIcon,
	smartphone: SmartphoneIcon,
	'app-window': AppWindowIcon,
	'file-code': FileCodeIcon,
	binary: BinaryIcon,
	brain: BrainIcon,
	cpu: CpuIcon,
	'file-signature': FileSignatureIcon,
	'circle-help': CircleHelpIcon,
	sparkles: SparklesIcon,
	plus: PlusIcon,
	minus: MinusIcon,
	'circle-check': CircleCheckIcon,
	'octagon-alert': OctagonAlertIcon,
	'door-open': DoorOpenIcon,
	'door-closed': DoorClosedIcon,
	banknote: BanknoteIcon
};

export const EVENT_TONE: Record<string, string> = {
	info: 'text-info',
	warning: 'text-warning',
	muted: 'text-muted-foreground'
};

export const EVENT_TONE_BG: Record<string, string> = {
	info: 'bg-info/10',
	warning: 'bg-warning/10',
	muted: 'bg-muted'
};

export function assetIcon(icon: string): IconComponent {
	return ASSET_ICONS[icon] ?? CircleHelpIcon;
}

export const PROGRAM_STATE_LABELS: Record<ProgramState, string> = {
	[ProgramState.Public]: 'Public',
	[ProgramState.Private]: 'Private'
};

export const SUBMISSION_STATE_LABELS: Record<SubmissionState, string> = {
	[SubmissionState.Open]: 'Open',
	[SubmissionState.Paused]: 'Paused',
	[SubmissionState.Closed]: 'Closed',
	[SubmissionState.Unknown]: 'Not reported'
};

export const SOURCE_LABELS: Record<string, string> = {
	api: 'Platform API',
	feed: 'Bounty Targets feed'
};

export const SOURCE_NOTES: Record<string, string> = {
	api: 'Read from the platform with your credentials — includes private programs.',
	feed: 'Public programs republished by arkadiyt/bounty-targets-data. Public scope only.'
};

const PAYOUT_FORMAT = new Intl.NumberFormat('en', {
	notation: 'compact',
	maximumFractionDigits: 1
});

export function formatPayout(
	min: number | null,
	max: number | null,
	currency: string | null
): string | null {
	if (!max && !min) return null;
	const symbol = !currency || currency.toUpperCase() === 'USD' ? '$' : `${currency} `;
	if (min && max && min !== max)
		return `${symbol}${PAYOUT_FORMAT.format(min)}–${PAYOUT_FORMAT.format(max)}`;
	return `up to ${symbol}${PAYOUT_FORMAT.format(max ?? min ?? 0)}`;
}

export const SCOPE_STATE_LABELS: Record<ScopeState, string> = {
	[ScopeState.InScope]: 'In scope',
	[ScopeState.OutOfScope]: 'Out of scope'
};

export const ASSET_GROUP_LABELS: Record<AssetGroup, string> = {
	[AssetGroup.Network]: 'Network',
	[AssetGroup.Mobile]: 'Mobile',
	[AssetGroup.Code]: 'Code',
	[AssetGroup.Other]: 'Other'
};

export const PROGRAM_SORTS = [
	{ value: 'age', label: 'Newest' },
	{ value: 'name', label: 'Name' },
	{ value: 'payout', label: 'Highest payout' },
	{ value: 'reports', label: 'Most reports' }
] as const;

export const SCOPE_TABS = [
	{ value: 'all', label: 'All scope' },
	{ value: ScopeState.InScope, label: 'In scope' },
	{ value: ScopeState.OutOfScope, label: 'Out of scope' }
] as const;

export const SYNC_INTERVAL_LABELS: Record<string, string> = {
	off: 'Manual only',
	six_hours: 'Every 6 hours',
	daily: 'Every day',
	weekly: 'Every week'
};

export const SEARCH_DEBOUNCE_MS = 250;
export const EVENT_PAGE_SIZE = 50;
export const PROGRAM_PAGE_SIZE = 25;

export const MAX_IMPORT_TAGS = 10;

export const PLATFORM_LABELS: Record<string, string> = {
	hackerone: 'HackerOne',
	bugcrowd: 'Bugcrowd',
	intigriti: 'Intigriti',
	yeswehack: 'YesWeHack'
};
