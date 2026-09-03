import Globe from '@lucide/svelte/icons/globe';
import TerminalSquare from '@lucide/svelte/icons/terminal-square';
import Database from '@lucide/svelte/icons/database';
import Mail from '@lucide/svelte/icons/mail';
import Server from '@lucide/svelte/icons/server';
import CircleHelp from '@lucide/svelte/icons/circle-help';
import type { IconComponent } from './icons';

// mirrors shared/definitions/ports.py ServiceClass
export enum ServiceClass {
	WEB = 'web',
	REMOTE = 'remote',
	DATABASE = 'database',
	MAIL = 'mail',
	INFRA = 'infra',
	OTHER = 'other'
}

export const SERVICE_CLASS_ORDER: ServiceClass[] = [
	ServiceClass.WEB,
	ServiceClass.REMOTE,
	ServiceClass.DATABASE,
	ServiceClass.MAIL,
	ServiceClass.INFRA,
	ServiceClass.OTHER
];

export const SERVICE_CLASS_LABELS: Record<string, string> = {
	[ServiceClass.WEB]: 'Web',
	[ServiceClass.REMOTE]: 'Remote access',
	[ServiceClass.DATABASE]: 'Data store',
	[ServiceClass.MAIL]: 'Mail',
	[ServiceClass.INFRA]: 'Infrastructure',
	[ServiceClass.OTHER]: 'Other'
};

export const SERVICE_CLASS_ICONS: Record<string, IconComponent> = {
	[ServiceClass.WEB]: Globe,
	[ServiceClass.REMOTE]: TerminalSquare,
	[ServiceClass.DATABASE]: Database,
	[ServiceClass.MAIL]: Mail,
	[ServiceClass.INFRA]: Server,
	[ServiceClass.OTHER]: CircleHelp
};

// the validated categorical scale, assigned in fixed order; Other is the residual bucket
export const SERVICE_CLASS_FILL: Record<string, string> = {
	[ServiceClass.WEB]: 'var(--chart-1)',
	[ServiceClass.REMOTE]: 'var(--chart-4)',
	[ServiceClass.DATABASE]: 'var(--chart-3)',
	[ServiceClass.MAIL]: 'var(--chart-5)',
	[ServiceClass.INFRA]: 'var(--chart-2)',
	[ServiceClass.OTHER]: 'color-mix(in oklch, var(--muted-foreground) 35%, transparent)'
};

// mirrors shared/definitions/ports.py PortSource
export enum PortSource {
	NAABU = 'naabu',
	INTERNETDB = 'internetdb',
	HTTP_PROBE = 'http_probe',
	BANNER = 'banner'
}

export const PORT_SOURCE_LABELS: Record<string, string> = {
	naabu: 'Port scan',
	internetdb: 'External scanner',
	http_probe: 'HTTP probe',
	banner: 'Service banner'
};

export const PORT_SOURCE_HELP: Record<string, string> = {
	naabu: 'TCP connection completed by this scan',
	internetdb: 'Reported by an internet-wide scanner, not confirmed by this scan',
	http_probe: 'Answered an HTTP request from this scan',
	banner: 'Returned a service banner to this scan'
};

// mirrors shared/definitions/ports.py SCAN_POLICY_LABELS
export const SCAN_POLICY_LABELS: Record<string, string> = {
	full: 'Scanned in full',
	web: 'Web ports only',
	skip: 'Not scanned'
};

export function serviceClassLabel(key: string | null | undefined): string {
	return SERVICE_CLASS_LABELS[key ?? ''] ?? 'Other';
}
