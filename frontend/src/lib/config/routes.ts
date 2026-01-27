export const routeLabels: Record<string, string> = {
	dashboard: 'Dashboard',

	// Reconnaissance
	targets: 'Targets',
	scans: 'Scans',
	automation: 'Automation',
	engines: 'Scan Engines',
	contexts: 'Scan Contexts',

	// Intelligence
	vulnerabilities: 'Vulnerabilities',
	assets: 'Assets',
	subdomains: 'Subdomains',
	endpoints: 'Endpoints',
	ips: 'IP Addresses',
	technologies: 'Technologies',

	// Reporting
	reports: 'Reports',

	// Settings
	settings: 'Settings'
};

export function getRouteLabel(segment: string): string {
	return routeLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1);
}
