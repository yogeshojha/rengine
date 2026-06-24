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

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function getRouteLabel(segment: string): string {
	if (routeLabels[segment]) return routeLabels[segment];
	if (UUID_REGEX.test(segment)) return '';
	return segment.charAt(0).toUpperCase() + segment.slice(1);
}
