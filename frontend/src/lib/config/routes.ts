export const routeLabels: Record<string, string> = {
	dashboard: 'Dashboard',

	// Reconnaissance
	targets: 'Targets',
	scans: 'Scans',
	automation: 'Automation',
	engines: 'Scan Engines',
	contexts: 'Scan Contexts',
	schedules: 'Scheduled Scans',

	// Settings
	settings: 'Settings',

	profile: 'Profile'
};

export const SETTINGS_TABS = ['general', 'api-keys', 'proxies', 'notifications'] as const;
export type SettingsTab = (typeof SETTINGS_TABS)[number];

export const ROUTES = {
	login: '/login',
	dashboard: '/dashboard',
	onboarding: '/onboarding',
	profile: '/profile',
	targets: '/targets',
	target: (id: string) => `/targets/${id}`,
	scans: '/scans',
	scan: (id: string) => `/scans/${id}`,
	automation: '/automation',
	engines: '/automation/engines',
	engine: (id: string) => `/automation/engines/${id}`,
	contexts: '/automation/contexts',
	context: (id: string) => `/automation/contexts/${id}`,
	newContext: (projectId?: string) =>
		`/automation/contexts/new${projectId ? `?project=${projectId}` : ''}`,
	schedules: '/schedules',
	settings: (tab?: SettingsTab) => (tab ? `/settings?tab=${tab}` : '/settings')
} as const;

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getRouteLabel(segment: string): string {
	if (routeLabels[segment]) return routeLabels[segment];
	if (UUID_REGEX.test(segment)) return '';
	return segment.charAt(0).toUpperCase() + segment.slice(1);
}
