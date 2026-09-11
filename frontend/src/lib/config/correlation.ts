import Network from '@lucide/svelte/icons/network';
import Link2 from '@lucide/svelte/icons/link-2';
import Heading from '@lucide/svelte/icons/heading';
import Image from '@lucide/svelte/icons/image';
import FileDigit from '@lucide/svelte/icons/file-digit';
import Fingerprint from '@lucide/svelte/icons/fingerprint';
import FileBadge from '@lucide/svelte/icons/file-badge';
import ShieldCheck from '@lucide/svelte/icons/shield-check';
import List from '@lucide/svelte/icons/list';
import Layers from '@lucide/svelte/icons/layers';
import Server from '@lucide/svelte/icons/server';
import Cloud from '@lucide/svelte/icons/cloud';
import type { IconComponent } from './icons';

export const CORRELATION_TAB = 'correlation';

// mirrors shared/definitions/correlation.py CorrelationKind
export enum CorrelationKind {
	IP = 'ip',
	CNAME = 'cname',
	TITLE = 'title',
	FAVICON = 'favicon',
	BODY = 'content_hash',
	JARM = 'jarm',
	CERT = 'cert.fingerprint',
	CERT_ISSUER = 'cert.issuer',
	HEADERS = 'header_hash',
	TECH = 'tech',
	SERVER = 'server',
	CDN = 'cdn'
}

export const KIND_ICONS: Record<string, IconComponent> = {
	[CorrelationKind.IP]: Network,
	[CorrelationKind.CNAME]: Link2,
	[CorrelationKind.TITLE]: Heading,
	[CorrelationKind.FAVICON]: Image,
	[CorrelationKind.BODY]: FileDigit,
	[CorrelationKind.JARM]: Fingerprint,
	[CorrelationKind.CERT]: ShieldCheck,
	[CorrelationKind.CERT_ISSUER]: FileBadge,
	[CorrelationKind.HEADERS]: List,
	[CorrelationKind.TECH]: Layers,
	[CorrelationKind.SERVER]: Server,
	[CorrelationKind.CDN]: Cloud
};

// one hue per kind; infrastructure kinds at lower chroma
export const KIND_HUE: Record<string, number> = {
	[CorrelationKind.IP]: 255,
	[CorrelationKind.CNAME]: 200,
	[CorrelationKind.TITLE]: 150,
	[CorrelationKind.FAVICON]: 65,
	[CorrelationKind.BODY]: 300,
	[CorrelationKind.JARM]: 335,
	[CorrelationKind.CERT]: 5,
	[CorrelationKind.CERT_ISSUER]: 25,
	[CorrelationKind.HEADERS]: 278,
	[CorrelationKind.TECH]: 105,
	[CorrelationKind.SERVER]: 235,
	[CorrelationKind.CDN]: 180
};
const QUIET_KINDS: ReadonlySet<string> = new Set([
	CorrelationKind.TECH,
	CorrelationKind.SERVER,
	CorrelationKind.CDN
]);

export function kindColor(kind: string, dark: boolean, alpha = 1): string {
	const hue = KIND_HUE[kind] ?? 265;
	const quiet = QUIET_KINDS.has(kind);
	const l = dark ? 0.76 : 0.6;
	const c = quiet ? 0.07 : dark ? 0.15 : 0.17;
	return alpha === 1 ? `oklch(${l} ${c} ${hue})` : `oklch(${l} ${c} ${hue} / ${alpha})`;
}

// dashed ring for kinds close in hue
export const KIND_DASHED: ReadonlySet<string> = new Set([
	CorrelationKind.JARM,
	CorrelationKind.CERT,
	CorrelationKind.CERT_ISSUER
]);

export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 5;
