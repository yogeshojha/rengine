import Bug from '@lucide/svelte/icons/bug';
import Braces from '@lucide/svelte/icons/braces';
import Chrome from '@lucide/svelte/icons/chrome';
import CircleHelp from '@lucide/svelte/icons/circle-help';
import Cloud from '@lucide/svelte/icons/cloud';
import Cpu from '@lucide/svelte/icons/cpu';
import FileText from '@lucide/svelte/icons/file-text';
import FileWarning from '@lucide/svelte/icons/file-warning';
import Flame from '@lucide/svelte/icons/flame';
import Globe from '@lucide/svelte/icons/globe';
import IdCard from '@lucide/svelte/icons/id-card';
import KeyRound from '@lucide/svelte/icons/key-round';
import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
import Lock from '@lucide/svelte/icons/lock';
import Network from '@lucide/svelte/icons/network';
import Plug from '@lucide/svelte/icons/plug';
import ScanLine from '@lucide/svelte/icons/scan-line';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
import Unlink from '@lucide/svelte/icons/unlink';
import type { IconComponent } from './icons';

// mirrors shared/definitions/vulnerabilities.py Severity
export enum Severity {
	CRITICAL = 'critical',
	HIGH = 'high',
	MEDIUM = 'medium',
	LOW = 'low',
	INFO = 'info',
	UNKNOWN = 'unknown'
}

export const SEVERITY_ORDER: string[] = [
	Severity.CRITICAL,
	Severity.HIGH,
	Severity.MEDIUM,
	Severity.LOW,
	Severity.INFO,
	Severity.UNKNOWN
];

export const SEVERITY_LABELS: Record<string, string> = {
	[Severity.CRITICAL]: 'Critical',
	[Severity.HIGH]: 'High',
	[Severity.MEDIUM]: 'Medium',
	[Severity.LOW]: 'Low',
	[Severity.INFO]: 'Info',
	[Severity.UNKNOWN]: 'Unknown'
};

export const SEVERITY_HELP: Record<string, string> = {
	[Severity.CRITICAL]: 'Exploitable now, with system or data compromise as the outcome.',
	[Severity.HIGH]: 'Direct path to compromise, usually needing one more condition.',
	[Severity.MEDIUM]: 'Meaningful weakness that raises the cost of the next finding.',
	[Severity.LOW]: 'Hygiene defect with limited standalone impact.',
	[Severity.INFO]: 'An observation about the asset, not a weakness.',
	[Severity.UNKNOWN]: 'The check did not state a severity.'
};

// an ordinal risk ramp: danger reads as danger, and rank is carried by order and label too
export const SEVERITY_FILL: Record<string, string> = {
	[Severity.CRITICAL]: 'var(--destructive)',
	[Severity.HIGH]: 'var(--chart-4)',
	[Severity.MEDIUM]: 'var(--warning)',
	[Severity.LOW]: 'var(--chart-1)',
	[Severity.INFO]: 'color-mix(in oklch, var(--muted-foreground) 45%, transparent)',
	[Severity.UNKNOWN]: 'color-mix(in oklch, var(--muted-foreground) 30%, transparent)'
};

export const SEVERITY_TEXT: Record<string, string> = {
	[Severity.CRITICAL]: 'text-destructive',
	[Severity.HIGH]: 'text-[var(--chart-4)]',
	[Severity.MEDIUM]: 'text-warning',
	[Severity.LOW]: 'text-[var(--chart-1)]',
	[Severity.INFO]: 'text-muted-foreground',
	[Severity.UNKNOWN]: 'text-muted-foreground'
};

export const ACTIONABLE_SEVERITIES: string[] = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM];

export function severityRank(value: string | null | undefined): number {
	const index = SEVERITY_ORDER.indexOf(value ?? '');
	return index === -1 ? SEVERITY_ORDER.length : index;
}

export function severityLabel(value: string | null | undefined): string {
	return SEVERITY_LABELS[value ?? ''] ?? 'Unknown';
}

// mirrors shared/definitions/vulnerabilities.py VulnState
export enum VulnState {
	OPEN = 'open',
	CONFIRMED = 'confirmed',
	FALSE_POSITIVE = 'false_positive',
	ACCEPTED = 'accepted'
}

export const VULN_STATES: string[] = [
	VulnState.OPEN,
	VulnState.CONFIRMED,
	VulnState.FALSE_POSITIVE,
	VulnState.ACCEPTED
];

export const VULN_STATE_LABELS: Record<string, string> = {
	[VulnState.OPEN]: 'Open',
	[VulnState.CONFIRMED]: 'Confirmed',
	[VulnState.FALSE_POSITIVE]: 'False positive',
	[VulnState.ACCEPTED]: 'Risk accepted'
};

export const VULN_STATE_HELP: Record<string, string> = {
	[VulnState.OPEN]: 'Not yet reviewed.',
	[VulnState.CONFIRMED]: 'Reviewed and reproduced.',
	[VulnState.FALSE_POSITIVE]: 'Reviewed and rejected. Suppressed on later scans of this target.',
	[VulnState.ACCEPTED]: 'Reviewed and accepted. Kept out of the alerting path.'
};

export const SUPPRESSED_STATES: string[] = [VulnState.FALSE_POSITIVE, VulnState.ACCEPTED];

// mirrors shared/definitions/vulnerabilities.py Protocol
export const PROTOCOL_LABELS: Record<string, string> = {
	http: 'HTTP',
	network: 'Network',
	dns: 'DNS',
	ssl: 'TLS',
	file: 'File',
	headless: 'Browser',
	javascript: 'JavaScript',
	websocket: 'WebSocket',
	whois: 'WHOIS',
	other: 'Other'
};

export const PROTOCOL_ICONS: Record<string, IconComponent> = {
	http: Globe,
	network: Plug,
	dns: Network,
	ssl: Lock,
	file: FileText,
	headless: Chrome,
	javascript: Braces,
	websocket: ScanLine,
	whois: IdCard,
	other: CircleHelp
};

export const SCANNER_LABELS: Record<string, string> = { nuclei: 'Nuclei' };

// mirrors shared/definitions/vulnerabilities.py TEMPLATE_SETS ordering
export const TEMPLATE_SET_ICONS: Record<string, IconComponent> = {
	kev: Flame,
	cve: ShieldAlert,
	panel: LayoutDashboard,
	exposure: FileWarning,
	misconfiguration: SlidersHorizontal,
	'default-login': KeyRound,
	takeover: Unlink,
	injection: Bug,
	cloud: Cloud,
	network: Plug,
	ssl: Lock,
	dns: Network,
	headless: Chrome,
	technology: Cpu
};

export const TEMPLATE_SET_LABELS: Record<string, string> = {
	kev: 'Known exploited',
	cve: 'Published CVEs',
	panel: 'Exposed panels',
	exposure: 'Exposed data',
	misconfiguration: 'Misconfiguration',
	'default-login': 'Default credentials',
	takeover: 'Subdomain takeover',
	injection: 'Injection',
	cloud: 'Cloud storage',
	network: 'Network services',
	ssl: 'TLS and certificates',
	dns: 'DNS hygiene',
	headless: 'Browser checks',
	technology: 'Technology detection'
};

export const SURFACE_LABELS: Record<string, string> = {
	web: 'Web assets',
	services: 'Web assets and network services',
	full: 'Everything, including hostnames'
};

export const TEMPLATE_ORIGIN_LABELS: Record<string, string> = {
	official: 'Project templates',
	custom: 'Custom templates'
};

export const COVERAGE_STATUS_LABELS: Record<string, string> = {
	completed: 'Completed',
	partial: 'Partial',
	failed: 'Failed',
	skipped: 'Not run'
};

export const RISK_SIGNAL_LABELS: Record<string, string> = {
	kev: 'Known exploited',
	epss: 'Likely to be exploited',
	new: 'New',
	origin: 'Origin exposed'
};

export const MAX_TEMPLATE_UPLOAD = 50;
export const EPSS_HIGH = 0.5;
export const CVSS_HIGH = 7.0;

export const VULN_STAGE = 'vulnerability_scan';
