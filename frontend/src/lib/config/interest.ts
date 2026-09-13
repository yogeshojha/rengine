import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import Wrench from '@lucide/svelte/icons/wrench';
import KeyRound from '@lucide/svelte/icons/key-round';
import Building2 from '@lucide/svelte/icons/building-2';
import FlaskConical from '@lucide/svelte/icons/flask-conical';
import Archive from '@lucide/svelte/icons/archive';
import House from '@lucide/svelte/icons/house';
import LockOpen from '@lucide/svelte/icons/lock-open';
import FolderOpen from '@lucide/svelte/icons/folder-open';
import Bug from '@lucide/svelte/icons/bug';
import Plug from '@lucide/svelte/icons/plug';
import Flame from '@lucide/svelte/icons/flame';
import FileBadge from '@lucide/svelte/icons/file-badge';
import Unlink from '@lucide/svelte/icons/unlink';
import Network from '@lucide/svelte/icons/network';
import Layers from '@lucide/svelte/icons/layers';
import Image from '@lucide/svelte/icons/image';
import ShieldOff from '@lucide/svelte/icons/shield-off';
import Sparkle from '@lucide/svelte/icons/sparkle';
import Plus from '@lucide/svelte/icons/plus';
import Radar from '@lucide/svelte/icons/radar';
import ListFilter from '@lucide/svelte/icons/list-filter';
import Type from '@lucide/svelte/icons/type';
import Eye from '@lucide/svelte/icons/eye';
import type { IconComponent } from './icons';
import { INTEREST_BAND, INTEREST_SOURCE } from '$lib/types/interest';

export const INTEREST_TAB = 'interesting';

// mirrors shared/definitions/interest.py:InterestKind
export enum InterestKind {
	ADMIN_INTERFACE = 'admin_interface',
	DEVELOPER_TOOLING = 'developer_tooling',
	REMOTE_ACCESS = 'remote_access',
	BUSINESS_SYSTEM = 'business_system',
	NON_PRODUCTION = 'non_production',
	LEGACY = 'legacy',
	INTERNAL_NAMING = 'internal_naming',
	NO_AUTHENTICATION = 'no_authentication',
	EXPOSED_CONTENT = 'exposed_content',
	DIAGNOSTIC = 'diagnostic',
	SENSITIVE_SERVICE = 'sensitive_service',
	EXPLOITED_SOFTWARE = 'exploited_software',
	CERTIFICATE_ANOMALY = 'certificate_anomaly',
	TAKEOVER_RISK = 'takeover_risk',
	NETWORK_OUTLIER = 'network_outlier',
	RARE_TECHNOLOGY = 'rare_technology',
	RARE_IDENTITY = 'rare_identity',
	UNPROTECTED_EDGE = 'unprotected_edge',
	NEWLY_APPEARED = 'newly_appeared',
	OTHER = 'other'
}

export const KIND_ICONS: Record<string, IconComponent> = {
	[InterestKind.ADMIN_INTERFACE]: ShieldAlert,
	[InterestKind.DEVELOPER_TOOLING]: Wrench,
	[InterestKind.REMOTE_ACCESS]: KeyRound,
	[InterestKind.BUSINESS_SYSTEM]: Building2,
	[InterestKind.NON_PRODUCTION]: FlaskConical,
	[InterestKind.LEGACY]: Archive,
	[InterestKind.INTERNAL_NAMING]: House,
	[InterestKind.NO_AUTHENTICATION]: LockOpen,
	[InterestKind.EXPOSED_CONTENT]: FolderOpen,
	[InterestKind.DIAGNOSTIC]: Bug,
	[InterestKind.SENSITIVE_SERVICE]: Plug,
	[InterestKind.EXPLOITED_SOFTWARE]: Flame,
	[InterestKind.CERTIFICATE_ANOMALY]: FileBadge,
	[InterestKind.TAKEOVER_RISK]: Unlink,
	[InterestKind.NETWORK_OUTLIER]: Network,
	[InterestKind.RARE_TECHNOLOGY]: Layers,
	[InterestKind.RARE_IDENTITY]: Image,
	[InterestKind.UNPROTECTED_EDGE]: ShieldOff,
	[InterestKind.NEWLY_APPEARED]: Plus,
	[InterestKind.OTHER]: Eye
};

export const SOURCE_ICONS: Record<string, IconComponent> = {
	[INTEREST_SOURCE.KEYWORD]: Type,
	[INTEREST_SOURCE.RULE]: ListFilter,
	[INTEREST_SOURCE.CORRELATION]: Radar,
	[INTEREST_SOURCE.AI]: Sparkle
};

export function kindIcon(kind: string): IconComponent {
	return KIND_ICONS[kind] ?? Eye;
}

export function sourceIcon(source: string): IconComponent {
	return SOURCE_ICONS[source] ?? ListFilter;
}

export const BAND_RAIL: Record<string, string> = {
	[INTEREST_BAND.CRITICAL]: 'bg-destructive',
	[INTEREST_BAND.HIGH]: 'bg-warning',
	[INTEREST_BAND.NOTABLE]: 'bg-info'
};

export const BAND_TEXT: Record<string, string> = {
	[INTEREST_BAND.CRITICAL]: 'text-destructive',
	[INTEREST_BAND.HIGH]: 'text-warning',
	[INTEREST_BAND.NOTABLE]: 'text-info'
};

export const TONE_CHIP: Record<string, string> = {
	warning: 'border-warning/30 bg-warning/10 text-warning',
	info: 'border-info/25 bg-info/10 text-info',
	neutral: 'border-border bg-muted/60 text-muted-foreground'
};

export const AI_CHIP = 'border-info/40 bg-info/10 text-info';
export const RULE_CHIP = 'border-primary/30 bg-primary/[0.07] text-primary';

export function sourceChipClass(source: string): string {
	if (source === INTEREST_SOURCE.AI) return AI_CHIP;
	if (source === INTEREST_SOURCE.CORRELATION) return TONE_CHIP.neutral;
	return RULE_CHIP;
}

export const INTEREST_SORTS = [
	{ value: 'score', label: 'Exposure score' },
	{ value: 'host', label: 'Hostname' }
] as const;
