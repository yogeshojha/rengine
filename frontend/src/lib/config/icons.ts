import { TargetType } from '$lib/types/target';
import Github from '@lucide/svelte/icons/github';
import Globe from '@lucide/svelte/icons/globe';
import MapPin from '@lucide/svelte/icons/map-pin';
import Network from '@lucide/svelte/icons/network';
import Hash from '@lucide/svelte/icons/hash';
import Building2 from '@lucide/svelte/icons/building-2';
import Link2 from '@lucide/svelte/icons/link-2';
import Server from '@lucide/svelte/icons/server';
import Shield from '@lucide/svelte/icons/shield';
import Radar from '@lucide/svelte/icons/radar';
import Route from '@lucide/svelte/icons/route';
import ScanSearch from '@lucide/svelte/icons/scan-search';
import Biohazard from '@lucide/svelte/icons/biohazard';
import SatelliteDish from '@lucide/svelte/icons/satellite-dish';
import Package from '@lucide/svelte/icons/package';

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

export const PROVIDER_ICONS: Record<string, IconComponent> = {
	globe: Globe,
	shield: Shield,
	radar: Radar,
	route: Route,
	'scan-search': ScanSearch,
	biohazard: Biohazard,
	'satellite-dish': SatelliteDish,
	github: Github
};

export function getProviderIcon(icon: string): IconComponent {
	return PROVIDER_ICONS[icon] ?? Package;
}
