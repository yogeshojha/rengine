import AppWindowIcon from '@lucide/svelte/icons/app-window';
import AsteriskIcon from '@lucide/svelte/icons/asterisk';
import BinaryIcon from '@lucide/svelte/icons/binary';
import BrainIcon from '@lucide/svelte/icons/brain';
import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
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
	'circle-help': CircleHelpIcon
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
	[SubmissionState.Closed]: 'Closed'
};

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
	{ value: 'reports', label: 'Most reports' }
] as const;

export const SCOPE_TABS = [
	{ value: 'all', label: 'All scope' },
	{ value: ScopeState.InScope, label: 'In scope' },
	{ value: ScopeState.OutOfScope, label: 'Out of scope' }
] as const;

export const PROGRAM_PAGE_SIZE = 25;

export const PLATFORM_TAG = 'hackerone';
export const MAX_IMPORT_TAGS = 10;
