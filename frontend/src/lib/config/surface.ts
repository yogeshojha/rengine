import Globe from '@lucide/svelte/icons/globe';
import Waypoints from '@lucide/svelte/icons/waypoints';
import ServerCog from '@lucide/svelte/icons/server-cog';
import Network from '@lucide/svelte/icons/network';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import Package from '@lucide/svelte/icons/package';
import KeyRound from '@lucide/svelte/icons/key-round';
import type { IconComponent } from './icons';
import { STORAGE_KEYS } from './storage-keys';
import type { ScanRead } from '$lib/types/scan';

export enum SurfaceDimension {
	WEB_ASSETS = 'web_assets',
	ENDPOINTS = 'endpoints',
	SERVICES = 'services',
	IPS = 'ips',
	VULNERABILITIES = 'vulnerabilities',
	SOFTWARE = 'software',
	SECRETS = 'secrets'
}

export const RESULT_TABS = [
	'web-assets',
	'endpoints',
	'services',
	'ips',
	'vulnerabilities',
	'software',
	'secrets'
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
	recentsKey: string;
	kinds: string[];
	countColumns: (keyof ScanRead)[];
	// what a deleted row takes with it
	children?: string;
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
		recentsKey: STORAGE_KEYS.webAssetsRecentQueries,
		kinds: ['hosts', 'http_assets'],
		countColumns: ['subdomains_found', 'http_assets_found'],
		children: 'stored responses'
	},
	[SurfaceDimension.ENDPOINTS]: {
		key: SurfaceDimension.ENDPOINTS,
		label: 'Endpoints',
		noun: 'endpoint',
		nounPlural: 'endpoints',
		icon: Waypoints,
		tab: 'endpoints',
		queryParam: 'ep_q',
		recentsKey: STORAGE_KEYS.endpointsRecentQueries,
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
		recentsKey: STORAGE_KEYS.servicesRecentQueries,
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
		recentsKey: STORAGE_KEYS.ipsRecentQueries,
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
		recentsKey: STORAGE_KEYS.vulnsRecentQueries,
		kinds: ['vulnerabilities'],
		countColumns: ['vulnerabilities_found']
	},
	[SurfaceDimension.SOFTWARE]: {
		key: SurfaceDimension.SOFTWARE,
		label: 'Software',
		noun: 'software CVE',
		nounPlural: 'software CVEs',
		icon: Package,
		tab: 'software',
		queryParam: 'sw_q',
		recentsKey: STORAGE_KEYS.softwareRecentQueries,
		kinds: ['http_assets', 'ports'],
		countColumns: []
	},
	[SurfaceDimension.SECRETS]: {
		key: SurfaceDimension.SECRETS,
		label: 'Secrets',
		noun: 'secret',
		nounPlural: 'secrets',
		icon: KeyRound,
		tab: 'secrets',
		queryParam: 'sec_q',
		recentsKey: STORAGE_KEYS.secretRecentQueries,
		kinds: ['secrets'],
		countColumns: ['secrets_found'],
		children: 'sightings'
	}
};

export const FINDINGS_ROOT = SurfaceDimension.VULNERABILITIES;

export const FINDINGS_TABS = [
	{ key: SurfaceDimension.VULNERABILITIES, label: 'Findings' },
	{ key: SurfaceDimension.SOFTWARE, label: SURFACE[SurfaceDimension.SOFTWARE].label },
	{ key: SurfaceDimension.SECRETS, label: 'Secrets' },
	{ key: 'cve', label: 'CVEs' }
] as const;
export type FindingsTab = (typeof FINDINGS_TABS)[number]['key'];

export const SURFACE_ORDER: SurfaceSpec[] = [
	SURFACE[SurfaceDimension.WEB_ASSETS],
	SURFACE[SurfaceDimension.ENDPOINTS],
	SURFACE[SurfaceDimension.SERVICES],
	SURFACE[SurfaceDimension.IPS],
	SURFACE[SurfaceDimension.VULNERABILITIES],
	SURFACE[SurfaceDimension.SOFTWARE],
	SURFACE[SurfaceDimension.SECRETS]
];

export const ASSET_DIMENSIONS: SurfaceSpec[] = SURFACE_ORDER.filter(
	(spec) =>
		spec.key !== SurfaceDimension.VULNERABILITIES &&
		spec.key !== SurfaceDimension.SOFTWARE &&
		spec.key !== SurfaceDimension.SECRETS
);

export function surfaceSpec(key: string): SurfaceSpec | undefined {
	return SURFACE[key as SurfaceDimension];
}
