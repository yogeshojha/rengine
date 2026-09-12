import { FINDINGS_TABS, SURFACE, SURFACE_ORDER, type FindingsTab } from './surface';

export const routeLabels: Record<string, string> = {
	dashboard: 'Dashboard',

	surface: 'Attack surface',
	...Object.fromEntries(SURFACE_ORDER.map((spec) => [spec.tab, spec.label])),
	exposures: 'Exposures',
	cves: 'CVEs',
	cve: 'CVEs',

	// Discovery
	targets: 'Targets',
	scans: 'Scans',
	compare: 'Compare runs',
	connectors: 'Connectors',
	notes: 'Notes',
	'bounty-hub': 'Bounty Hub',

	reports: 'Reports',
	arsenal: 'Arsenal',

	// Automation
	automation: 'Scans',
	engines: 'Scan engines',
	contexts: 'Scan contexts',
	schedules: 'Schedules',

	// Settings
	settings: 'Settings',
	general: 'General',
	'api-keys': 'API keys',
	proxies: 'Proxies',
	notifications: 'Notifications',
	ai: 'AI',
	mcp: 'MCP',

	profile: 'Profile'
};

export const SETTINGS_SECTIONS = [
	'general',
	'api-keys',
	'proxies',
	'notifications',
	'bounty-hub',
	'ai',
	'mcp'
] as const;
export type SettingsSection = (typeof SETTINGS_SECTIONS)[number];

export const BOUNTY_HUB_TABS = ['watching', 'programs', 'updates'] as const;
export type BountyHubTab = (typeof BOUNTY_HUB_TABS)[number];

export const ARSENAL_TABS = ['nuclei', 'wordlists', 'threat-intel'] as const;
export const EXPOSURE_TABS = ['exposures', 'rules', 'dismissed'] as const;
export type ExposureTab = (typeof EXPOSURE_TABS)[number];
export const REPORT_TABS = ['reports', 'templates', 'themes', 'defaults'] as const;
export type ReportTab = (typeof REPORT_TABS)[number];

export const AI_TABS = ['connection', 'features', 'usage'] as const;
export const CONNECTOR_TABS = ['queue', 'discovered', 'settings'] as const;
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
	notes: '/notes',
	scansForTarget: (id: string) => `/scans?target=${id}`,
	surface: (tab: string, query?: Record<string, string>) => {
		const params = new URLSearchParams(query ?? {});
		const suffix = params.toString();
		return `/surface/${tab}${suffix ? `?${suffix}` : ''}`;
	},
	scan: (id: string) => `/scans/${id}`,
	cves: '/surface/cve',
	cve: (id: string) => `/surface/cve/${encodeURIComponent(id)}`,
	compare: (current: string, baseline?: string | null, query?: Record<string, string>) => {
		const params = new URLSearchParams({ current, ...(query ?? {}) });
		if (baseline) params.set('baseline', baseline);
		return `/scans/compare?${params.toString()}`;
	},
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
	schedules: '/automation/schedules',
	arsenal: (tab?: ArsenalTab) => (tab ? `/arsenal?tab=${tab}` : '/arsenal'),
	bountyHub: (handle?: string, platform?: string) =>
		handle ? `/bounty-hub?program=${handle}&platform=${platform ?? 'hackerone'}` : '/bounty-hub',
	bountyHubTab: (tab: BountyHubTab) => `/bounty-hub?tab=${tab}`,
	bountyWatch: (id: string) => `/bounty-hub?tab=watching&watch=${id}`,
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
	ai: (tab?: AiTab) => (tab ? `/settings/ai?tab=${tab}` : '/settings/ai'),
	mcp: (tab?: McpTab) => (tab ? `/settings/mcp?tab=${tab}` : '/settings/mcp'),
	connectors: (tab?: ConnectorTab) => (tab ? `/connectors?tab=${tab}` : '/connectors'),
	settings: (section?: SettingsSection) => (section ? `/settings/${section}` : '/settings')
} as const;

export const findingsHref = (key: FindingsTab): string =>
	key === 'cve' ? ROUTES.cves : ROUTES.surface(SURFACE[key].tab);

export const FINDINGS_PATHS: string[] = FINDINGS_TABS.map((tab) => findingsHref(tab.key));

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getRouteLabel(segment: string): string {
	if (routeLabels[segment]) return routeLabels[segment];
	if (UUID_REGEX.test(segment)) return '';
	return segment.charAt(0).toUpperCase() + segment.slice(1);
}
