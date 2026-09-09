import { SURFACE_ORDER } from './surface';

export const routeLabels: Record<string, string> = {
	dashboard: 'Dashboard',

	surface: 'Attack surface',
	...Object.fromEntries(SURFACE_ORDER.map((spec) => [spec.tab, spec.label])),

	// Reconnaissance
	targets: 'Targets',
	scans: 'Scans',
	automation: 'Automation',
	engines: 'Scan engines',
	contexts: 'Scan contexts',
	schedules: 'Schedules',

	// Tools
	arsenal: 'Arsenal',
	exposures: 'Exposures',
	connectors: 'Connectors',
	bountyHub: 'Bounty Hub',

	// Reporting
	reports: 'Reports',
	ai: 'AI',
	mcp: 'MCP',

	// Settings
	settings: 'Settings',

	profile: 'Profile'
};

export const SETTINGS_TABS = [
	'general',
	'api-keys',
	'proxies',
	'notifications',
	'bounty-hub'
] as const;
export type SettingsTab = (typeof SETTINGS_TABS)[number];

export const BOUNTY_HUB_TABS = ['programs', 'updates'] as const;
export type BountyHubTab = (typeof BOUNTY_HUB_TABS)[number];

export const ARSENAL_TABS = ['nuclei', 'wordlists', 'threat-intel'] as const;
export const EXPOSURE_TABS = ['exposures', 'rules', 'dismissed'] as const;
export type ExposureTab = (typeof EXPOSURE_TABS)[number];
export const REPORT_TABS = ['reports', 'templates', 'themes', 'defaults'] as const;
export type ReportTab = (typeof REPORT_TABS)[number];

export const AI_TABS = ['connection', 'features', 'usage'] as const;
export const CONNECTOR_TABS = ['queue', 'discovered', 'coverage', 'sessions', 'settings'] as const;
export type ConnectorTab = (typeof CONNECTOR_TABS)[number];
export const MCP_TABS = ['server', 'tools', 'access', 'activity'] as const;
export type McpTab = (typeof MCP_TABS)[number];
export type AiTab = (typeof AI_TABS)[number];
export type ArsenalTab = (typeof ARSENAL_TABS)[number];

export const ROUTES = {
	login: '/login',
	dashboard: '/dashboard',
	onboarding: '/onboarding',
	profile: '/profile',
	targets: '/targets',
	target: (id: string, tab?: string) => (tab ? `/targets/${id}?tab=${tab}` : `/targets/${id}`),
	scans: '/scans',
	scansForTarget: (id: string) => `/scans?target=${id}`,
	surface: (tab: string, query?: Record<string, string>) => {
		const params = new URLSearchParams(query ?? {});
		const suffix = params.toString();
		return `/surface/${tab}${suffix ? `?${suffix}` : ''}`;
	},
	scan: (id: string) => `/scans/${id}`,
	scanTab: (id: string, tab: string, query?: Record<string, string>) => {
		const params = new URLSearchParams({ tab, ...(query ?? {}) });
		return `/scans/${id}?${params.toString()}`;
	},
	automation: '/automation',
	engines: '/automation/engines',
	engine: (id: string) => `/automation/engines/${id}`,
	contexts: '/automation/contexts',
	context: (id: string) => `/automation/contexts/${id}`,
	newContext: (projectId?: string, template?: string) => {
		const params = new URLSearchParams();
		if (projectId) params.set('project', projectId);
		if (template) params.set('template', template);
		const query = params.toString();
		return `/automation/contexts/new${query ? `?${query}` : ''}`;
	},
	schedules: '/schedules',
	arsenal: (tab?: ArsenalTab) => (tab ? `/arsenal?tab=${tab}` : '/arsenal'),
	bountyHub: (handle?: string, platform?: string) =>
		handle ? `/bounty-hub?program=${handle}&platform=${platform ?? 'hackerone'}` : '/bounty-hub',
	bountyHubTab: (tab: BountyHubTab) => `/bounty-hub?tab=${tab}`,
	exposures: (tab?: ExposureTab, query?: Record<string, string>) => {
		const params = new URLSearchParams(query ?? {});
		if (tab) params.set('tab', tab);
		const suffix = params.toString();
		return `/exposures${suffix ? `?${suffix}` : ''}`;
	},
	reports: (tab?: ReportTab) => (tab ? `/reports?tab=${tab}` : '/reports'),
	report: (id: string) => `/reports/${id}`,
	reportTemplate: (id: string) => `/reports/templates/${id}`,
	reportsForScan: (scanId: string) => `/reports?scan=${scanId}`,
	reportsForTarget: (targetId: string) => `/reports?target=${targetId}`,
	ai: (tab?: AiTab) => (tab ? `/ai?tab=${tab}` : '/ai'),
	mcp: (tab?: McpTab) => (tab ? `/mcp?tab=${tab}` : '/mcp'),
	connectors: (tab?: ConnectorTab) => (tab ? `/connectors?tab=${tab}` : '/connectors'),
	settings: (tab?: SettingsTab) => (tab ? `/settings?tab=${tab}` : '/settings')
} as const;

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getRouteLabel(segment: string): string {
	if (routeLabels[segment]) return routeLabels[segment];
	if (UUID_REGEX.test(segment)) return '';
	return segment.charAt(0).toUpperCase() + segment.slice(1);
}
