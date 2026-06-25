import { TargetType } from '$lib/types/target';
import Globe from '@lucide/svelte/icons/globe';
import MapPin from '@lucide/svelte/icons/map-pin';
import Network from '@lucide/svelte/icons/network';
import Hash from '@lucide/svelte/icons/hash';
import Building2 from '@lucide/svelte/icons/building-2';
import Link2 from '@lucide/svelte/icons/link-2';
import Server from '@lucide/svelte/icons/server';

export type IconComponent = typeof Globe;

export const TARGET_TYPE_ICONS: Record<TargetType, IconComponent> = {
	[TargetType.DOMAIN]: Globe,
	[TargetType.IP]: MapPin,
	[TargetType.IP_RANGE]: Network,
	[TargetType.ASN]: Building2,
	[TargetType.URL]: Link2
};

export const TARGET_TYPE_ICONS_COMPACT: Record<TargetType, IconComponent> = {
	...TARGET_TYPE_ICONS,
	[TargetType.IP_RANGE]: Hash
};

export function getTargetTypeIcon(type: TargetType, compact = false): IconComponent {
	const map = compact ? TARGET_TYPE_ICONS_COMPACT : TARGET_TYPE_ICONS;
	return map[type] ?? Globe;
}

export const LOOKUP_TYPE_ICONS: Record<string, IconComponent> = {
	DOMAIN: Globe,
	IP: Server,
	ASN: Network
};

export function getLookupTypeIcon(type: string): IconComponent {
	return LOOKUP_TYPE_ICONS[type] ?? Globe;
}
