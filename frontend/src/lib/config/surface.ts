import Globe from '@lucide/svelte/icons/globe';
import Waypoints from '@lucide/svelte/icons/waypoints';
import ServerCog from '@lucide/svelte/icons/server-cog';
import Network from '@lucide/svelte/icons/network';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import type { IconComponent } from './icons';
import type { ScanRead } from '$lib/types/scan';

export enum SurfaceDimension {
	WEB_ASSETS = 'web_assets',
	ENDPOINTS = 'endpoints',
	SERVICES = 'services',
	IPS = 'ips',
	VULNERABILITIES = 'vulnerabilities'
}

export const RESULT_TABS = [
	'web-assets',
	'endpoints',
	'services',
	'ips',
	'vulnerabilities'
] as const;
export type ResultTab = (typeof RESULT_TABS)[number];

export interface SurfaceSpec {
	key: SurfaceDimension;
	label: string;
	noun: string;
	nounPlural: string;
	icon: IconComponent;
	tab: ResultTab;
	queryParam: string;
	kinds: string[];
	countColumns: (keyof ScanRead)[];
}

export const SURFACE: Record<SurfaceDimension, SurfaceSpec> = {
	[SurfaceDimension.WEB_ASSETS]: {
		key: SurfaceDimension.WEB_ASSETS,
		label: 'Web assets',
		noun: 'web asset',
		nounPlural: 'web assets',
		icon: Globe,
		tab: 'web-assets',
		queryParam: 'q',
		kinds: ['hosts', 'http_assets'],
		countColumns: ['subdomains_found', 'http_assets_found']
	},
	[SurfaceDimension.ENDPOINTS]: {
		key: SurfaceDimension.ENDPOINTS,
		label: 'Endpoints',
		noun: 'endpoint',
		nounPlural: 'endpoints',
		icon: Waypoints,
		tab: 'endpoints',
		queryParam: 'ep_q',
		kinds: ['endpoints'],
		countColumns: ['endpoints_found']
	},
	[SurfaceDimension.SERVICES]: {
		key: SurfaceDimension.SERVICES,
		label: 'Services',
		noun: 'service',
		nounPlural: 'services',
		icon: ServerCog,
		tab: 'services',
		queryParam: 'svc_q',
		kinds: ['ports'],
		countColumns: ['open_ports_found']
	},
	[SurfaceDimension.IPS]: {
		key: SurfaceDimension.IPS,
		label: 'IP addresses',
		noun: 'address',
		nounPlural: 'addresses',
		icon: Network,
		tab: 'ips',
		queryParam: 'ip_q',
		kinds: ['addresses'],
		countColumns: ['ips_found']
	},
	[SurfaceDimension.VULNERABILITIES]: {
		key: SurfaceDimension.VULNERABILITIES,
		label: 'Vulnerabilities',
		noun: 'finding',
		nounPlural: 'findings',
		icon: ShieldAlert,
		tab: 'vulnerabilities',
		queryParam: 'vuln_q',
		kinds: ['vulnerabilities'],
		countColumns: ['vulnerabilities_found']
	}
};

export const SURFACE_ORDER: SurfaceSpec[] = [
	SURFACE[SurfaceDimension.WEB_ASSETS],
	SURFACE[SurfaceDimension.ENDPOINTS],
	SURFACE[SurfaceDimension.SERVICES],
	SURFACE[SurfaceDimension.IPS],
	SURFACE[SurfaceDimension.VULNERABILITIES]
];

export function surfaceSpec(key: string): SurfaceSpec | undefined {
	return SURFACE[key as SurfaceDimension];
}
