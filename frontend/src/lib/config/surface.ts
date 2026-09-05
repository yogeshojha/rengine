import Globe from '@lucide/svelte/icons/globe';
import Waypoints from '@lucide/svelte/icons/waypoints';
import Plug from '@lucide/svelte/icons/plug';
import Server from '@lucide/svelte/icons/server';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import type { IconComponent } from './icons';

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
}

export const SURFACE: Record<SurfaceDimension, SurfaceSpec> = {
	[SurfaceDimension.WEB_ASSETS]: {
		key: SurfaceDimension.WEB_ASSETS,
		label: 'Web Assets',
		noun: 'web asset',
		nounPlural: 'web assets',
		icon: Globe,
		tab: 'web-assets',
		queryParam: 'q',
		kinds: ['hosts', 'http_assets']
	},
	[SurfaceDimension.ENDPOINTS]: {
		key: SurfaceDimension.ENDPOINTS,
		label: 'Endpoints',
		noun: 'endpoint',
		nounPlural: 'endpoints',
		icon: Waypoints,
		tab: 'endpoints',
		queryParam: 'ep_q',
		kinds: ['endpoints']
	},
	[SurfaceDimension.SERVICES]: {
		key: SurfaceDimension.SERVICES,
		label: 'Services',
		noun: 'service',
		nounPlural: 'services',
		icon: Plug,
		tab: 'services',
		queryParam: 'svc_q',
		kinds: ['ports']
	},
	[SurfaceDimension.IPS]: {
		key: SurfaceDimension.IPS,
		label: 'IPs',
		noun: 'address',
		nounPlural: 'addresses',
		icon: Server,
		tab: 'ips',
		queryParam: 'ip_q',
		kinds: ['addresses']
	},
	[SurfaceDimension.VULNERABILITIES]: {
		key: SurfaceDimension.VULNERABILITIES,
		label: 'Vulnerabilities',
		noun: 'finding',
		nounPlural: 'findings',
		icon: ShieldAlert,
		tab: 'vulnerabilities',
		queryParam: 'vuln_q',
		kinds: ['vulnerabilities']
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
