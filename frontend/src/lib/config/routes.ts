import { CHANNEL_ORDER, type ChannelKind } from './channels';
import { FINDINGS_TABS, SURFACE, SURFACE_ORDER, type FindingsTab } from './surface';

export const routeLabels: Record<string, string> = {
	dashboard: 'Dashboard',

	surface: 'Attack surface',
	assets: 'Assets',
	engineSetup: 'Scan setup',
	operations: 'Operations',
	integrations: 'Integrations',
	...Object.fromEntries(SURFACE_ORDER.map((spec) => [spec.tab, spec.label])),
	exposures: 'Exposures',
	cves: 'CVEs',
	cve: 'CVEs',

	// Discovery
	targets: 'Targets',
	scans: 'Scans',
	compare: 'Compare runs',
	connectors: 'Connectors',
	'issue-trackers': 'Issue trackers',
	'remote-control': 'Remote control',
	agents: 'Agents',
	notes: 'Notes',
	tripwires: 'Tripwires',
	'whats-new': "What's new",
	'bounty-hub': 'Bounty Hub',
	programs: 'Programs',

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
	users: 'Users',

	profile: 'Profile'
};

export const SETTINGS_SECTIONS = [
	'general',
	'api-keys',
	'proxies',
	'notifications',
	'ai',
	'users'
] as const;
export type SettingsSection = (typeof SETTINGS_SECTIONS)[number];
export const ADMIN_SETTINGS: readonly SettingsSection[] = [
	'api-keys',
	'proxies',
	'notifications',
	'users'
];

export const BOUNTY_HUB_TABS = ['watching', 'programs', 'updates'] as const;
export type BountyHubTab = (typeof BOUNTY_HUB_TABS)[number];

export const ARSENAL_TABS = ['nuclei', 'wordlists', 'threat-intel'] as const;
export const PANEL_PARAM = 'panel';
export const CALLBACK_PANEL = 'callback-server';
export const BOUNTY_SETTINGS_PANEL = 'settings';
export const EXPOSURE_TABS = ['exposures', 'rules', 'dismissed'] as const;
export type ExposureTab = (typeof EXPOSURE_TABS)[number];
export const REPORT_TABS = ['reports', 'templates', 'themes', 'typefaces', 'branding'] as const;
export type ReportTab = (typeof REPORT_TABS)[number];

export const AI_SECTIONS = ['connection', 'features', 'usage'] as const;
export const CONNECTOR_TABS = ['queue', 'discovered', 'settings'] as const;
export const ISSUE_TRACKER_TABS = ['issues', 'trackers', 'routes'] as const;
export type IssueTrackerTab = (typeof ISSUE_TRACKER_TABS)[number];
export type ConnectorTab = (typeof CONNECTOR_TABS)[number];
export const REMOTE_CONTROL_TABS = CHANNEL_ORDER;
export type RemoteControlTab = ChannelKind;
export type AiSection = (typeof AI_SECTIONS)[number];
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
	tripwires: (query?: Record<string, string>) => {
		const params = new URLSearchParams(query ?? {});
		const suffix = params.toString();
		return `/tripwires${suffix ? `?${suffix}` : ''}`;
	},
	scansForTarget: (id: string) => `/scans?target=${id}`,
	scansWhere: (query: Record<string, string>) => `/scans?${new URLSearchParams(query).toString()}`,
	whatsNew: (query?: Record<string, string>) => {
		const params = new URLSearchParams(query ?? {});
		const suffix = params.toString();
		return `/whats-new${suffix ? `?${suffix}` : ''}`;
	},
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
	results: (tab: string, scanId?: string | null, query?: Record<string, string>) =>
		scanId ? ROUTES.scanTab(scanId, tab, query) : ROUTES.surface(tab, query),
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
	callbackServer: () => `/arsenal?${PANEL_PARAM}=${CALLBACK_PANEL}`,
	bountyHubSettings: () => `/bounty-hub?${PANEL_PARAM}=${BOUNTY_SETTINGS_PANEL}`,
	bountyHub: (handle?: string, platform?: string) =>
		handle ? `/bounty-hub?program=${handle}&platform=${platform ?? 'hackerone'}` : '/bounty-hub',
	bountyHubTab: (tab: BountyHubTab) => `/bounty-hub?tab=${tab}`,
	bountyReports: (platform: string, program?: string) =>
		program
			? `/bounty-hub/${platform}?program=${encodeURIComponent(program)}`
			: `/bounty-hub/${platform}`,
	bountyWatch: (id: string) => `/bounty-hub?tab=watching&watch=${id}`,
	exposures: (tab?: ExposureTab, query?: Record<string, string>) => {
		const params = new URLSearchParams(query ?? {});
		if (tab) params.set('tab', tab);
		const suffix = params.toString();
		return `/exposures${suffix ? `?${suffix}` : ''}`;
	},
	reports: (tab?: ReportTab) => (tab ? `/reports?tab=${tab}` : '/reports'),
	reportTemplate: (id: string) => `/reports/templates/${id}`,
	reportsForScan: (scanId: string) => `/reports?scan=${scanId}`,
	reportsForTarget: (targetId: string) => `/reports?target=${targetId}`,
	ai: (section?: AiSection) => (section ? `/settings/ai#ai-${section}` : '/settings/ai'),
	agents: () => '/agents',
	connectors: (tab?: ConnectorTab) => (tab ? `/connectors?tab=${tab}` : '/connectors'),
	issueTrackers: (tab?: IssueTrackerTab) =>
		tab ? `/issue-trackers?tab=${tab}` : '/issue-trackers',
	remoteControl: (tab?: RemoteControlTab) =>
		tab ? `/remote-control?tab=${tab}` : '/remote-control',
	settings: (section?: SettingsSection) => (section ? `/settings/${section}` : '/settings')
} as const;

/** A detail page belongs to one project; switching projects returns to its list. */
const PROJECT_SWITCH_REDIRECTS: { match: RegExp; list: string }[] = [
	{ match: /^\/targets\/[^/]+/, list: ROUTES.targets },
	{ match: /^\/scans\/[^/]+/, list: ROUTES.scans },
	{ match: /^\/automation\/engines\/[^/]+/, list: ROUTES.engines },
	{ match: /^\/automation\/contexts\/[^/]+/, list: ROUTES.contexts }
];

export function projectSwitchRedirect(path: string): string | null {
	return PROJECT_SWITCH_REDIRECTS.find((r) => r.match.test(path))?.list ?? null;
}

export const findingsHref = (key: FindingsTab): string =>
	key === 'cve' ? ROUTES.cves : ROUTES.surface(SURFACE[key].tab);

export const FINDINGS_PATHS: string[] = FINDINGS_TABS.map((tab) => findingsHref(tab.key));

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getRouteLabel(segment: string): string {
	if (routeLabels[segment]) return routeLabels[segment];
	if (UUID_REGEX.test(segment)) return '';
	return segment.charAt(0).toUpperCase() + segment.slice(1);
}
