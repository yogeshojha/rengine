import { Capability, InstanceMode, type CapabilityKey } from '$lib/config/capabilities';

export const DASHBOARD_ROWS = [
	'estate',
	'findings',
	'programs',
	'posture',
	'scanning',
	'composition'
] as const;
export type DashboardRow = (typeof DASHBOARD_ROWS)[number];

export const DASHBOARD_ROW_LABELS: Record<DashboardRow, string> = {
	estate: 'Estate',
	findings: 'Findings',
	programs: 'Programs',
	posture: 'Posture',
	scanning: 'Scanning',
	composition: 'Composition'
};

export interface DashboardWidgetSpec {
	id: string;
	label: string;
	row: DashboardRow;
	modes: InstanceMode[];
	capability?: CapabilityKey;
}

const BOTH = [InstanceMode.BugBounty, InstanceMode.Corporate];
const BB = [InstanceMode.BugBounty];
const CORP = [InstanceMode.Corporate];

export const DASHBOARD_WIDGETS: DashboardWidgetSpec[] = [
	{ id: 'funnel', label: 'Attack surface funnel', row: 'estate', modes: BOTH },
	{ id: 'inventory', label: 'Inventory', row: 'estate', modes: BOTH },
	{ id: 'changes', label: 'Attack surface changes', row: 'estate', modes: BOTH },
	{ id: 'geo', label: 'Geography', row: 'estate', modes: BOTH },
	{ id: 'board', label: 'Board', row: 'findings', modes: BOTH },
	{ id: 'findings-trend', label: 'Findings by severity', row: 'findings', modes: BOTH },
	{ id: 'exploitation', label: 'Exploitation', row: 'findings', modes: BOTH },
	{ id: 'evidence', label: 'Evidence', row: 'findings', modes: BOTH },
	{ id: 'exposures', label: 'Exposures', row: 'findings', modes: BOTH },
	{
		id: 'programs',
		label: 'Platform events',
		row: 'programs',
		modes: BB,
		capability: Capability.BOUNTY_PROGRAMS
	},
	{
		id: 'watches',
		label: 'Watched programs',
		row: 'programs',
		modes: BB,
		capability: Capability.PROGRAM_WATCHES
	},
	{ id: 'connectors', label: 'Browsing', row: 'programs', modes: BB },
	{ id: 'certs', label: 'Certificates', row: 'posture', modes: CORP },
	{ id: 'hygiene', label: 'Web hygiene', row: 'posture', modes: CORP },
	{ id: 'ownership', label: 'Ownership', row: 'posture', modes: CORP },
	{ id: 'runs', label: 'Scan activity', row: 'scanning', modes: BOTH },
	{ id: 'software', label: 'Software CVEs', row: 'scanning', modes: BOTH },
	{ id: 'services', label: 'Services', row: 'composition', modes: BOTH },
	{ id: 'tech', label: 'Technology', row: 'composition', modes: BOTH },
	{ id: 'hosting', label: 'Hosting', row: 'composition', modes: BOTH },
	{ id: 'shared', label: 'Shared across targets', row: 'composition', modes: BOTH },
	{ id: 'activity', label: 'Activity', row: 'composition', modes: BOTH }
];

export type DashboardWidgetId = (typeof DASHBOARD_WIDGETS)[number]['id'];

export const widgetSpec = (id: string) => DASHBOARD_WIDGETS.find((w) => w.id === id);

export function widgetAvailable(spec: DashboardWidgetSpec, capabilities: string[]): boolean {
	return !spec.capability || capabilities.includes(spec.capability);
}

export function widgetDefaultOn(spec: DashboardWidgetSpec, mode: InstanceMode): boolean {
	return spec.modes.includes(mode);
}
