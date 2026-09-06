export const routeLabels: Record<string, string> = {
	dashboard: 'Dashboard',

	// Reconnaissance
	targets: 'Targets',
	scans: 'Scans',
	automation: 'Automation',
	engines: 'Scan Engines',
	contexts: 'Scan Contexts',
	schedules: 'Scheduled Scans',

	// Tools
	arsenal: 'Tools Arsenal',

	// Reporting
	reports: 'Reports',
	ai: 'AI',

	// Settings
	settings: 'Settings',

	profile: 'Profile'
};

export const SETTINGS_TABS = ['general', 'api-keys', 'proxies', 'notifications'] as const;
export type SettingsTab = (typeof SETTINGS_TABS)[number];

export const ARSENAL_TABS = ['nuclei', 'wordlists'] as const;
export const REPORT_TABS = ['reports', 'templates', 'themes', 'defaults'] as const;
export type ReportTab = (typeof REPORT_TABS)[number];

export const AI_TABS = ['connection', 'features', 'usage'] as const;
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
	reports: (tab?: ReportTab) => (tab ? `/reports?tab=${tab}` : '/reports'),
	report: (id: string) => `/reports/${id}`,
	reportTemplate: (id: string) => `/reports/templates/${id}`,
	reportsForScan: (scanId: string) => `/reports?scan=${scanId}`,
	reportsForTarget: (targetId: string) => `/reports?target=${targetId}`,
	ai: (tab?: AiTab) => (tab ? `/ai?tab=${tab}` : '/ai'),
	settings: (tab?: SettingsTab) => (tab ? `/settings?tab=${tab}` : '/settings')
} as const;

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getRouteLabel(segment: string): string {
	if (routeLabels[segment]) return routeLabels[segment];
	if (UUID_REGEX.test(segment)) return '';
	return segment.charAt(0).toUpperCase() + segment.slice(1);
}
